from app.news_ingest import run_news_loop

WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
    "JPM", "V", "WMT", "PG", "JNJ", "DIS", "NFLX"
]

if __name__ == "__main__":
    run_news_loop(WATCHLIST, interval_seconds=60)
