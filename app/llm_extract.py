from dotenv import load_dotenv
load_dotenv(".env")

import os
import json
from openai import OpenAI

client = OpenAI(api_key=(os.getenv("OPENAI_API_KEY") or "").strip())

SYSTEM = """You are a strict classifier for automated trading safety.
Return ONLY valid JSON (no markdown).
Schema:
{"trade_allowed": boolean, "confidence": number, "reason": string}
"""

def classify_news(ticker: str, title: str, description: str) -> dict:
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Ticker: {ticker}\nTitle: {title}\nDescription: {description}"}
        ],
    )
    return json.loads(resp.output_text)

if __name__ == "__main__":
    print(classify_news(
        "AAPL",
        "Apple shares rise after earnings beat expectations",
        "Apple reported strong earnings and raised guidance."
    ))
