import os
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
