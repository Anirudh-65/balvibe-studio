import time
import requests

BASE = "http://127.0.0.1:8000"

print("--- 1. Checking Health and Config ---")
health = requests.get(f"{BASE}/api/health", timeout=10).json()
print("Health:", health)
assert health["ok"] is True
assert all(health["providers"].values()), f"Not all providers configured: {health['providers']}"

config = requests.get(f"{BASE}/api/config", timeout=10).json()
print("Languages available:", len(config["languages"]))
print("TTS providers:", list(config["ttsProviders"].keys()))

print("\n--- 2. Stage 1: Generate Storyline Flow ---")
gen = requests.post(
    f"{BASE}/api/generate-storyline",
    json={
        "instruction": "Show six numbers for exactly 2 seconds. Hide one number and ask which number disappeared. Include one practice round and three formal trials, then close without correctness feedback.",
        "ageBand": "6-8",
        "duration": 120,
        "targetLanguage": "hi-IN",
    },
    timeout=120,
).json()
run_id = gen["runId"]
print("Created Run ID:", run_id)
print("Flow title:", gen["storylineFlow"]["title"])
print("Flow steps:", len(gen["storylineFlow"]["flowSteps"]))

print("\n--- 3. Approve Storyline Flow ---")
app_flow = requests.post(
    f"{BASE}/api/runs/{run_id}/approve-storyline",
    json={"storylineFlow": gen["storylineFlow"]},
    timeout=30,
).json()
print("Flow status:", app_flow["status"])

print("\n--- 4. Stage 2: Generate Script from Flow ---")
script = requests.post(
    f"{BASE}/api/runs/{run_id}/generate-script",
    timeout=120,
).json()
scenes = script["storyline"]["scenes"]
print("Generated script scenes:", len(scenes))
for sc in scenes[:2]:
    print(f"  Scene {sc['sceneOrder']}: {sc['audioScript'][:60]}...")

print("\n--- 5. Approve Script ---")
app_script = requests.post(
    f"{BASE}/api/runs/{run_id}/approve",
    json={"storyline": script["storyline"]},
    timeout=30,
).json()
print("Script approved:", app_script["approved"])

print("\n--- 6. Stage 3: Translate Narration (Sarvam) ---")
trans = requests.post(
    f"{BASE}/api/runs/{run_id}/translate",
    json={"targetLanguage": "hi-IN", "provider": "sarvam"},
    timeout=120,
).json()
print("Translated scenes count:", len(trans["storyline"]["scenes"]))

print("\n--- 7. Stage 4: Voiceover (Azure Speech) ---")
voice = requests.post(
    f"{BASE}/api/runs/{run_id}/voiceover",
    json={"provider": "azure", "voice": "hi-IN-SwaraNeural", "fps": 30},
    timeout=180,
).json()
print("Azure voiceover combined duration:", voice["audioTimelineDurationMs"], "ms")
print("Azure combined audio URL:", voice["combinedAudioUrl"])

print("\n--- 8. Retrieve Dataset Attachment ---")
ds = requests.get(f"{BASE}/api/runs/{run_id}/dataset", timeout=10)
print("Dataset response code:", ds.status_code)
assert ds.status_code == 200
dataset_obj = ds.json()
print("Dataset scenes:", len(dataset_obj["scenes"]))

print("\n--- 9. Retrieve Scene Audio WAV File ---")
first_scene = dataset_obj["scenes"][0]
audio_url = first_scene["audioUrl"]
aud_res = requests.get(f"{BASE}{audio_url}", timeout=10)
print("Scene audio WAV status:", aud_res.status_code, "bytes:", len(aud_res.content))
assert aud_res.status_code == 200
assert len(aud_res.content) > 1000

print("\n=======================================================")
print("SUCCESS: ALL APIS PLACED CORRECTLY AND WORKING 100%!")
print("=======================================================")
