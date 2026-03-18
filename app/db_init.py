import os
import psycopg

def init_database():
    """Initialize database tables on startup"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("WARNING: DATABASE_URL not set, skipping init")
        return
    
    # Railway uses postgres://, but psycopg needs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg.connect(db_url)
    conn.autocommit = True
    
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_raw (
                id SERIAL PRIMARY KEY,
                ticker TEXT NOT NULL,
                source TEXT,
                headline TEXT,
                ts TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_features (
                id SERIAL PRIMARY KEY,
                ticker TEXT NOT NULL,
                sentiment_score FLOAT,
                relevance_score FLOAT,
                extracted_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trade_intents (
                id SERIAL PRIMARY KEY,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL,
                tv_price FLOAT,
                tv_score FLOAT,
                tv_atr FLOAT,
                tv_stop FLOAT,
                tv_takeprofit FLOAT,
                decision TEXT,
                reason TEXT,
                ts TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id SERIAL PRIMARY KEY,
                ticker TEXT NOT NULL,
                order_data JSONB,
                ts TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    
    conn.close()
    print("✅ Database tables initialized")
