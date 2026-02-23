import os, json
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
