import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv(",env")
load_dotenv(".env")

print("=== Checking Environment Variables ===")
groq_key = os.getenv("GROQ_API_KEY")
sarvam_key = os.getenv("SARVAM_API_KEY")
bhashini_user = os.getenv("BHASHINI_USER_ID")
bhashini_key = os.getenv("BHASHINI_API_KEY")
azure_key = os.getenv("AZURE_SPEECH_KEY")
azure_region = os.getenv("AZURE_SPEECH_REGION", "centralindia")

print(f"GROQ_API_KEY set: {bool(groq_key)}")
print(f"SARVAM_API_KEY set: {bool(sarvam_key)}")
print(f"BHASHINI credentials set: {bool(bhashini_user and bhashini_key)}")
print(f"AZURE credentials set: {bool(azure_key and azure_region)}")

# 1. Test Groq
print("\n--- 1. Testing Groq API ---")
try:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json={
            "model": "qwen/qwen3.8-27b",
            "temperature": 0.35,
            "max_completion_tokens": 50,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": "respond JSON: {\"status\": \"ok\"}"}],
        },
        timeout=30,
    )
    print(f"Groq status: {r.status_code}, response: {r.text[:200]}")
except Exception as e:
    print(f"Groq error: {e}")

# 2. Test Sarvam Translate
print("\n--- 2. Testing Sarvam Translate API ---")
try:
    r = requests.post(
        "https://api.sarvam.ai/translate",
        headers={"api-subscription-key": sarvam_key, "content-type": "application/json"},
        json={
            "input": "Hello world",
            "source_language_code": "en-IN",
            "target_language_code": "hi-IN",
            "model": "sarvam-translate:v1",
            "mode": "formal",
        },
        timeout=30,
    )
    print(f"Sarvam Translate status: {r.status_code}, body: {r.json()}")
except Exception as e:
    print(f"Sarvam Translate error: {e}")

# 3. Test Sarvam TTS
print("\n--- 3. Testing Sarvam Bulbul TTS API ---")
try:
    r = requests.post(
        "https://api.sarvam.ai/text-to-speech",
        headers={"api-subscription-key": sarvam_key, "content-type": "application/json"},
        json={
            "text": "नमस्ते दुनिया",
            "language_code": "hi-IN",
            "model": "bulbul:v3",
            "speaker": "ritu",
            "speech_sample_rate": 24000,
            "output_audio_codec": "wav",
        },
        timeout=30,
    )
    print(f"Sarvam TTS status: {r.status_code}, audio present: {bool(r.json().get('audios'))}")
except Exception as e:
    print(f"Sarvam TTS error: {e}")

# 4. Test Azure Speech TTS
print("\n--- 4. Testing Azure Speech TTS ---")
try:
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="hi-IN">'
        '<voice name="hi-IN-SwaraNeural"><prosody rate="-5%">नमस्ते</prosody></voice></speak>'
    )
    endpoint = f"https://{azure_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    r = requests.post(
        endpoint,
        headers={
            "Ocp-Apim-Subscription-Key": azure_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
            "User-Agent": "BalVibe-Studio",
        },
        data=ssml.encode("utf-8"),
        timeout=30,
    )
    print(f"Azure Speech status: {r.status_code}, audio length bytes: {len(r.content) if r.ok else r.text[:200]}")
except Exception as e:
    print(f"Azure Speech error: {e}")

# 5. Test Bhashini ULCA
print("\n--- 5. Testing Bhashini ULCA Pipeline ---")
try:
    from app.config import load_settings
    from app.bhashini import translate_text_bhashini
    s = load_settings()
    # If load_settings didn't pick up ,env, manually set credentials
    res = translate_text_bhashini("Hello world", "hi-IN", s)
    print(f"Bhashini translation result: {res}")
except Exception as e:
    print(f"Bhashini error: {e}")
