import os
import time
import requests
from datetime import datetime, timedelta
from app.store import Store
from app.llm_extract import extract_features

POLYGON_KEY = os.getenv("POLYGON_API_KEY")
store = Store()

def ingest_polygon_news(ticker: str, lookback_hours=1):
    """Fetch recent news for a ticker from Polygon"""
    if not POLYGON_KEY:
        return []
    
    url = f"https://api.polygon.io/v2/reference/news"
    params = {
        "ticker": ticker,
        "limit": 10,
        "apiKey": POLYGON_KEY
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        
        articles = resp.json().get("results", [])
        return articles
    except Exception as e:
        print(f"Polygon error for {ticker}: {e}")
        return []

def ingest_gdelt_news(keywords: str, lookback_hours=1):
    """Fetch recent news from GDELT DOC API"""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": keywords,
        "mode": "artlist",
        "maxrecords": 25,
        "format": "json",
        "timespan": f"{lookback_hours}h"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        articles = data.get("articles", [])
        return articles
    except Exception as e:
        print(f"GDELT error: {e}")
        return []

def process_article(article: dict, source: str, ticker: str = None):
    """Store raw article, extract features via LLM, store features"""
    
    if store.article_exists(article.get("url")):
        return
    
    raw_id = store.insert_news_raw(
        source=source,
        ticker=ticker,
        published_at=article.get("published_utc") or article.get("seendate"),
        title=article.get("title"),
        url=article.get("url") or article.get("url"),
        content=article.get("description", "") or article.get("socialimage", "")
    )
    
    features = extract_features(article)
    
    if features:
        store.insert_news_features(
            url=article.get("url"),
            ticker=features.get("ticker") or ticker,
            event_type=features.get("event_type"),
            sentiment=features.get("sentiment"),
            urgency=features.get("urgency"),
            relevance=features.get("relevance"),
            risk_flag=features.get("risk_flag"),
            trade_bias=features.get("trade_bias"),
            confidence=features.get("confidence"),
            rationale=features.get("rationale")
        )

def run_news_loop(watchlist: list, interval_seconds=60):
    """Main loop: continuously ingest news for watchlist"""
    print(f"Starting news ingestion loop for {len(watchlist)} tickers...")
    
    while True:
        try:
            for ticker in watchlist:
                articles = ingest_polygon_news(ticker)
                for art in articles:
                    process_article(art, source="polygon", ticker=ticker)
                
                time.sleep(0.5)
            
            gdelt_articles = ingest_gdelt_news("stock market OR earnings OR SEC", lookback_hours=1)
            for art in gdelt_articles[:10]:
                process_article(art, source="gdelt")
            
            print(f"[{datetime.utcnow()}] News ingestion cycle complete. Sleeping {interval_seconds}s...")
            time.sleep(interval_seconds)
            
        except Exception as e:
            print(f"News loop error: {e}")
            time.sleep(10)
