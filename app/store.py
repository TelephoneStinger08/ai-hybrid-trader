import os
import psycopg
from app.schemas import TVSignal

class Store:
    def __init__(self):
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self.db_url = db_url

    def _conn(self):
        return psycopg.connect(self.db_url)

    def insert_trade_intent(self, sig: TVSignal):
        q = """
        insert into trade_intents(ticker, side, tv_price, tv_score, tv_atr, tv_stop, tv_takeprofit, decision, reason)
        values (%s,%s,%s,%s,%s,%s,%s,'PENDING','')
        """
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(q, (sig.ticker, sig.action, sig.price, sig.score, sig.atr, sig.stop, sig.takeprofit))
            conn.commit()

    def update_trade_intent_decision(self, sig: TVSignal, decision: str, reason: str):
        q = """
        update trade_intents
        set decision=%s, reason=%s
        where ticker=%s and side=%s and ts=(select max(ts) from trade_intents where ticker=%s and side=%s)
        """
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(q, (decision, reason, sig.ticker, sig.action, sig.ticker, sig.action))
            conn.commit()

    def insert_execution(self, ticker: str, order_data: dict):
        import json
        q = "insert into executions(ticker, order_data) values (%s,%s)"
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(q, (ticker, json.dumps(order_data)))
            conn.commit()

    def get_latest_news_features(self, ticker: str):
        q = "select sentiment_score, relevance_score from news_features where ticker=%s order by extracted_at desc limit 1"
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(q, (ticker,))
            row = c.fetchone()
            return row if row else None
