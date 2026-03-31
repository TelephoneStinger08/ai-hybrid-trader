from fastapi import FastAPI, HTTPException
from app.schemas import TVSignal
from app.store import Store
from app.risk import RiskEngine
from app.broker_alpaca import AlpacaBroker
from app.utils import now_utc
from app.db_init import init_database
import os

app = FastAPI(title="AI Hybrid Trader - Short Only")

@app.on_event("startup")
def startup_event():
    init_database()

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

    action = sig.action.upper()
    if action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="bad action")

    store.insert_trade_intent(sig)

    ok, reason = risk_engine.pre_trade_checks(sig.ticker, action, sig.price)
    if not ok:
        store.update_trade_intent_decision(sig, "REJECT", reason)
        return {"decision": "REJECT", "reason": reason}

    live = os.getenv("LIVE_TRADING", "false").lower() == "true"
    order = broker.submit_short_only(sig.ticker, action, sig.price, live=live)

    store.insert_execution(sig.ticker, order)
    store.update_trade_intent_decision(sig, "EXECUTE", "passed gates")
    
    return {"decision": "EXECUTE", "order": order}
