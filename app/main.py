from dotenv import load_dotenv
load_dotenv(".env")

import os
import traceback
import requests
from flask import Flask, request, jsonify

from app.llm_extract import classify_news
from app.news_ingest import fetch_polygon_news

app = Flask(__name__)

ALPACA_BASE_URL = (os.getenv("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets").strip()
ALPACA_API_KEY = (os.getenv("ALPACA_API_KEY") or "").strip()
ALPACA_SECRET_KEY = (os.getenv("ALPACA_SECRET_KEY") or "").strip()

WEBHOOK_SECRET = (os.getenv("WEBHOOK_SECRET") or "").strip()
DEFAULT_NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", "3"))

def alpaca_place_order(symbol: str, qty: int, side: str, order_type: str = "market", tif: str = "day"):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": order_type,
        "time_in_force": tif,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

@app.route("/tv-webhook", methods=["POST"])
@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    # Parse JSON
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    # Auth: accept either header secret (curl) OR JSON body secret (TradingView)
    if WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Webhook-Secret", "")
        body_secret = (payload.get("secret") or "").strip()
        if header_secret != WEBHOOK_SECRET and body_secret != WEBHOOK_SECRET:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

    # Normalize inputs early (so they exist for BOTH equity and crypto)
    symbol = (payload.get("symbol") or "").upper().strip()
    side = (payload.get("side") or "").lower().strip()

    # qty safe parse (never crashes)
    try:
        qty = int(payload.get("qty") or 1)
    except Exception:
        qty = 1

    if not symbol or side not in ("buy", "sell"):
        return jsonify({"ok": False, "error": "missing_symbol_or_side"}), 400

    # --- CRYPTO TEST MODE ---
    crypto_symbol = symbol.endswith("USD") or ("/" in symbol)
    if crypto_symbol:
        # normalize common format for Alpaca crypto
        if symbol in ("BTCUSD", "ETHUSD", "SOLUSD"):
            symbol = symbol.replace("USD", "/USD")
        decision = {
            "trade_allowed": True,
            "confidence": 0.6,
            "reason": "Crypto mode: skipping equity news gate."
        }
    else:
        # Pull latest news (Polygon)
        news_raw = fetch_polygon_news(ticker=symbol, limit=DEFAULT_NEWS_LIMIT)
        items = news_raw.get("results") or []

        if not items:
            decision = {"trade_allowed": True, "confidence": 0.5, "reason": "No recent news returned."}
        else:
            top = items[0]
            title = top.get("title") or ""
            desc = top.get("description") or ""
            decision = classify_news(symbol, title, desc)

    # Gate trade
    if not decision.get("trade_allowed", False):
        return jsonify({
            "ok": True,
            "executed": False,
            "symbol": symbol,
            "decision": decision,
            "reason": "Blocked by AI gate"
        }), 200

    # Place order
    try:
        order = alpaca_place_order(symbol=symbol, qty=qty, side=side)
    except Exception as e:
        return jsonify({"ok": False, "error": "alpaca_order_failed", "detail": str(e)}), 500

    return jsonify({
        "ok": True,
        "executed": True,
        "symbol": symbol,
        "decision": decision,
        "order": order
    }), 200
