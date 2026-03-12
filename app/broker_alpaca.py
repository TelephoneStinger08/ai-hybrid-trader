import os, requests

class AlpacaBroker:
    def __init__(self):
        self.key = os.getenv("ALPACA_KEY_ID")
        self.secret = os.getenv("ALPACA_SECRET_KEY")
        self.base = os.getenv("ALPACA_BASE_URL", "https://api.alpaca.markets")

    def _headers(self):
        return {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json",
        }

    def submit_short_only(self, ticker: str, action: str, ref_price: float, live: bool):
        if not live:
            base = "https://paper-api.alpaca.markets"
        else:
            base = self.base

        max_notional = float(os.getenv("MAX_ORDER_NOTIONAL_USD", "250"))
        
        if action == "SELL":
            # Open short position
            payload = {
                "symbol": ticker,
                "notional": str(max_notional),
                "side": "sell",
                "type": "market",
                "time_in_force": "day"
            }
        elif action == "BUY":
            # Close short position (buy to cover)
            pos = requests.get(f"{base}/v2/positions/{ticker}", headers=self._headers(), timeout=10)
            if pos.status_code != 200:
                return {"status": "rejected", "error": "no position to cover", "details": pos.text}
            qty = abs(float(pos.json().get("qty")))  # Get absolute value of short position
            payload = {
                "symbol": ticker,
                "qty": str(qty),
                "side": "buy",
                "type": "market",
                "time_in_force": "day"
            }
        else:
            return {"status": "rejected", "error": "invalid action"}

        r = requests.post(f"{base}/v2/orders", headers=self._headers(), json=payload, timeout=10)
        return r.json()
