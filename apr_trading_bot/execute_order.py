import requests
import os

url = "https://paper-api.alpaca.markets/v2/orders"

headers = {
    "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY"),
    "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY"),
    "Content-Type": "application/json"
}

payload = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "market",
    "time_in_force": "day"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
