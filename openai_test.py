import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

resp = client.responses.create(
    model="gpt-4.1-mini",
    input="Reply with exactly: OK"
)

print(resp.output_text)
