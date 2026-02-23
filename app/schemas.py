from pydantic import BaseModel

class TVSignal(BaseModel):
    secret: str
    ticker: str
    action: str
    price: float
    score: float
    atr: float
    stop: float
    takeprofit: float
    ts: str
