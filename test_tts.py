"""
Quick test to verify Sarvam Bulbul v3 TTS works with your API key.
Run: python test_tts.py
"""

import os
import sys

# Load .env file manually (no dependency needed)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

API_KEY = os.environ.get("SARVAM_API_KEY", "").strip()
if not API_KEY:
    print("ERROR: SARVAM_API_KEY not set. Add it to .env or set as env var.")
    sys.exit(1)

import json
import base64
from urllib.request import Request, urlopen
from urllib.error import HTTPError

payload = json.dumps({
    "text": "नमस्ते! मैं ओली हूँ। चलिए शुरू करते हैं।",
    "language_code": "hi-IN",
    "model": "bulbul:v3",
    "speaker": "shubh",
    "sample_rate": 24000,
}).encode("utf-8")

req = Request(
    "https://api.sarvam.ai/text-to-speech",
    data=payload,
    headers={
        "api-subscription-key": API_KEY,
        "Content-Type": "application/json",
    },
    method="POST",
)

print("Calling Sarvam TTS (Bulbul v3)...")
try:
    with urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
except HTTPError as e:
    error_body = e.read().decode("utf-8", errors="replace")
    print(f"ERROR: Sarvam TTS failed ({e.code}): {error_body}")
    sys.exit(1)

audios = body.get("audios", [])
if not audios or not audios[0]:
    print("ERROR: No audio data returned.")
    sys.exit(1)

output_path = os.path.join(os.path.dirname(__file__), "hindi_test.wav")
with open(output_path, "wb") as f:
    f.write(base64.b64decode(audios[0]))

print(f"Done! Hindi audio saved as {output_path}")
print("Open the file and verify the voice sounds correct.")
