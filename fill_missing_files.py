import os

files = {
    "app/utils.py": '''from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc).isoformat()
''',

    "app/schemas.py": '''from pydantic import BaseModel

class TVSignal(BaseModel):
    secret: str
    ticker: str
    action: str  # "BUY" or "SELL"
    price: float
    score: float
    atr: float
    stop: float
    takeprofit: float
    ts: str
''',

    "app/store.py": '''import os, json
import psycopg
from psycopg.rows import dict_row

DB = os.getenv("DATABASE_URL")

class Store:
    def _conn(self):
        return psycopg.connect(DB, row_factory=dict_row)

    def insert_trade_intent(self, sig):
        q = """
        insert into trade_intents(ticker, side, tv_price, tv_score, tv_atr, tv_stop, tv_takeprofit, decision, decision_reason)
        values (%s,%s,%s,%s,%s,%s,%s,'PENDING','')
        """
        with self._conn() as c:
            c.execute(q, (sig.ticker, sig.action, sig.price, sig.score, sig.atr, sig.stop, sig.takeprofit))
            c.commit()

    def update_trade_intent_decision(self, sig, decision, reason):
        q = """
        update trade_intents
        set decision=%s, decision_reason=%s
        where ticker=%s and side=%s and tv_price=%s
        order by ts desc
        limit 1
        """
        with self._conn() as c:
            c.execute(q, (decision, reason, sig.ticker, sig.action, sig.price))
            c.commit()

    def get_latest_news_features(self, ticker: str):
        q = """
        select * from news_features
        where ticker=%s
        order by extracted_at desc
        limit 1
        """
        with self._conn() as c:
            r = c.execute(q, (ticker,)).fetchone()
            return r

    def insert_execution(self, ticker: str, order: dict):
        q = """
        insert into executions(ticker, alpaca_order_id, status, qty, notional, submitted_price, raw_response)
        values (%s,%s,%s,%s,%s,%s,%s)
        """
        with self._conn() as c:
            c.execute(q, (
                ticker,
                order.get("id"),
                order.get("status"),
                float(order.get("qty", 0) or 0),
                float(order.get("notional", 0) or 0),
                float(order.get("filled_avg_price", 0) or 0),
                json.dumps(order),
            ))
            c.commit()

    def article_exists(self, url: str) -> bool:
        q = "select 1 from news_raw where url=%s limit 1"
        with self._conn() as c:
            return c.execute(q, (url,)).fetchone() is not None

    def insert_news_raw(self, source, ticker, published_at, title, url, content):
        q = """
        insert into news_raw(source, ticker, published_at, title, url, content)
        values (%s,%s,%s,%s,%s,%s)
        on conflict (url) do nothing
        """
        with self._conn() as c:
            c.execute(q, (source, ticker, published_at, title, url, content))
            c.commit()

    def insert_news_features(self, url, ticker, event_type, sentiment, urgency, relevance, risk_flag, trade_bias, confidence, rationale):
        q = """
        insert into news_features(url, ticker, event_type, sentiment, urgency, relevance, risk_flag, trade_bias, confidence, rationale)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (url) do nothing
        """
        with self._conn() as c:
            c.execute(q, (url, ticker, event_type, sentiment, urgency, relevance, risk_flag, trade_bias, confidence, rationale))
            c.commit()
''',

    "app/risk.py": '''import os
import redis

REDIS_URL = os.getenv("REDIS_URL")

class RiskEngine:
    def __init__(self):
        self.r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    def pre_trade_checks(self, ticker: str, action: str, price: float):
        if action == "BUY":
            key = f"cooldown:{ticker}"
            if self.r.get(key):
                return False, "cooldown active"
        return True, "ok"

    def news_gate(self, action: str, nf):
        if nf is None:
            return True, "no news features; TA-only"

        if nf.get("risk_flag"):
            return False, "news risk_flag true"

        trade_bias = (nf.get("trade_bias") or "").upper()
        conf = float(nf.get("confidence") or 0)
        rel = float(nf.get("relevance") or 0)
        sent = float(nf.get("sentiment") or 0)

        if action == "BUY":
            if trade_bias in ("BEARISH", "SELL"):
                return False, "news bearish"
            if conf < 0.55 and rel < 0.60:
                return False, "news too uncertain"
            if sent < -0.35 and conf >= 0.55:
                return False, "negative sentiment"
        return True, "news ok"
''',

    "app/broker_alpaca.py": '''import os, requests

class AlpacaBroker:
    def __init__(self):
        self.key = os.getenv("ALPACA_KEY_ID")
        self.secret = os.getenv("ALPACA_SECRET_KEY")
        self.base = os.getenv("ALPACA_BASE_URL", "https://api.alpaca.markets")

    def _headers(self):
        return {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json",
        }

    def submit_long_only(self, ticker: str, action: str, ref_price: float, live: bool):
        if not live:
            base = "https://paper-api.alpaca.markets"
        else:
            base = self.base

        max_notional = float(os.getenv("MAX_ORDER_NOTIONAL_USD", "250"))
        
        if action == "BUY":
            payload = {
                "symbol": ticker,
                "notional": str(max_notional),
                "side": "buy",
                "type": "market",
                "time_in_force": "day"
            }
        else:
            pos = requests.get(f"{base}/v2/positions/{ticker}", headers=self._headers(), timeout=10)
            if pos.status_code != 200:
                return {"status": "rejected", "error": "no position to sell", "details": pos.text}
            qty = pos.json().get("qty")
            payload = {
                "symbol": ticker,
                "qty": str(qty),
                "side": "sell",
                "type": "market",
                "time_in_force": "day"
            }

        r = requests.post(f"{base}/v2/orders", headers=self._headers(), json=payload, timeout=10)
        return r.json()
''',

    "app/main.py": '''from fastapi import FastAPI, HTTPException
from app.schemas import TVSignal
from app.store import Store
from app.risk import RiskEngine
from app.broker_alpaca import AlpacaBroker
from app.utils import now_utc
import os

app = FastAPI(title="AI Hybrid Trader")

store = Store()
risk_engine = RiskEngine()
broker = AlpacaBroker()

@app.get("/health")
def health():
    return {"ok": True, "ts": now_utc()}

@app.post("/tv/webhook")
def tv_webhook(sig: TVSignal):
    expected = os.getenv("TV_WEBHOOK_SECRET", "changeme")
    if sig.secret != expected:
        raise HTTPException(status_code=401, detail="bad secret")

    if sig.action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="bad action")

    store.insert_trade_intent(sig)

    ok, reason = risk_engine.pre_trade_checks(sig.ticker, sig.action, sig.price)
    if not ok:
        store.update_trade_intent_decision(sig, "REJECT", reason)
        return {"decision": "REJECT", "reason": reason}

    nf = store.get_latest_news_features(sig.ticker)
    ok2, reason2 = risk_engine.news_gate(sig.action, nf)
    if not ok2:
        store.update_trade_intent_decision(sig, "REJECT", reason2)
        return {"decision": "REJECT", "reason": reason2}

    live = os.getenv("LIVE_TRADING", "false").lower() == "true"
    order = broker.submit_long_only(sig.ticker, sig.action, sig.price, live=live)

    store.insert_execution(sig.ticker, order)
    store.update_trade_intent_decision(sig, "EXECUTE", "passed gates")
    
    return {"decision": "EXECUTE", "order": order}
''',
}

for filepath, content in files.items():
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"✓ {filepath}")

print("\n✅ All files filled!")
