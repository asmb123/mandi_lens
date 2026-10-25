import os

from sarvamai import SarvamAI
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("SARVAM_API_KEY is missing. Add it to backend/.env before running this script.")

client = SarvamAI(api_subscription_key=api_key)
response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[{"role": "user", "content": "नमस्ते! अपना परिचय दीजिए।"}],
)
print(response.choices[0].message.content)
