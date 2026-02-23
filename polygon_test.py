import os, requests

API_KEY = (os.getenv("POLYGON_API_KEY") or "").strip()
symbol = "AAPL"

url = "https://api.polygon.io/v2/reference/news"
params = {
    "ticker": symbol,
    "limit": 5,
    "apiKey": API_KEY
}

r = requests.get(url, params=params, timeout=20)
print("STATUS:", r.status_code)
print("URL:", r.url)
r.raise_for_status()

data = r.json()
for item in data.get("results", []):
    print("-", item.get("published_utc"), item.get("title"))
