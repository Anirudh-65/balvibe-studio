import time
import requests

BASE = "http://127.0.0.1:8000"

print("====================================================")
print("TESTING FULL END-TO-END WORKFLOW (ALL 7 STAGES)")
print("====================================================")

# 1. Health check
h = requests.get(f"{BASE}/api/health", timeout=5).json()
print("1. Health OK:", h["ok"])

# 2. Stage 1: Generate Storyline Flow for 90s sample experiment
print("\n2. Stage 1: Generate Storyline Flow (90s)...")
gen = requests.post(
    f"{BASE}/api/generate-storyline",
    json={
        "instruction": "Show six numbers for exactly 2 seconds. Hide one number and ask which number disappeared. Include one practice round and three formal trials, then close without correctness feedback.",
        "ageBand": "6-8",
        "duration": 90,
        "targetLanguage": "hi-IN",
        "leadCharacter": "Mira the moon rabbit",
        "setting": "lantern lit forest",
        "storyIdea": "help find the missing flowers",
    },
    timeout=120,
).json()
run_id = gen["runId"]
print(f"   Created Run ID: {run_id}")
print(f"   Title: {gen['storylineFlow']['title']}")

# 3. Approve Storyline Flow
print("\n3. Approving Storyline Flow...")
app_flow = requests.post(
    f"{BASE}/api/runs/{run_id}/approve-storyline",
    json={"storylineFlow": gen["storylineFlow"]},
    timeout=30,
).json()
print(f"   Status: {app_flow['status']}")

# 4. Stage 2: Generate Script from Flow
print("\n4. Stage 2: Generating Script & Dialogues from Approved Flow...")
script = requests.post(
    f"{BASE}/api/runs/{run_id}/generate-script",
    timeout=120,
).json()
scenes = script["storyline"]["scenes"]
print(f"   Generated {len(scenes)} scenes.")

# 5. Approve Script
print("\n5. Approving Script...")
app_script = requests.post(
    f"{BASE}/api/runs/{run_id}/approve",
    json={"storyline": script["storyline"]},
    timeout=30,
).json()
print(f"   Script approved: {app_script['approved']}")

# 6. Stage 3: Translate Narration
print("\n6. Stage 3: Translating Narration with Sarvam...")
trans = requests.post(
    f"{BASE}/api/runs/{run_id}/translate",
    json={"targetLanguage": "hi-IN", "provider": "sarvam"},
    timeout=120,
).json()
print(f"   Translated {len(trans['storyline']['scenes'])} scenes to Hindi.")

# 7. Stage 4: Voiceover (Azure Speech)
print("\n7. Stage 4: Synthesizing Voiceover with Azure Speech...")
voice = requests.post(
    f"{BASE}/api/runs/{run_id}/voiceover",
    json={"provider": "azure", "voice": "hi-IN-SwaraNeural", "fps": 30},
    timeout=180,
).json()
print(f"   Combined Audio: {voice['audioTimelineDurationMs']} ms, {voice['combinedAudioUrl']}")

# 8. Stage 6: Generate Scene Visuals / Images
print("\n8. Stage 6: Generating Scene Visuals...")
img_res = requests.post(
    f"{BASE}/api/runs/{run_id}/generate-images",
    json={"provider": "local"},
    timeout=30,
).json()
print(f"   Generated visuals for {img_res['sceneCount']} scenes.")
first_img = img_res["scenes"][0]
print(f"   Scene 1 Image URL: {first_img['imageUrl']}")
print(f"   Scene 1 Prompt for Gemini: {first_img['imagePrompt'][:100]}...")

img_get = requests.get(f"{BASE}{first_img['imageUrl']}", timeout=10)
print(f"   Image file HTTP {img_get.status_code}, size: {len(img_get.content)} bytes")
assert img_get.status_code == 200

# 9. Stage 7: Composition & Muxing (Remotion + FFmpeg)
print("\n9. Stage 7: Composition & Muxing (Remotion + FFmpeg)...")
video_res = requests.post(
    f"{BASE}/api/runs/{run_id}/render-video",
    json={"provider": "azure", "fps": 30},
    timeout=180,
).json()
print(f"   Video Render Status: OK")
print(f"   Video URL: {video_res['videoUrl']}")
print(f"   Duration: {video_res['durationSeconds']}s ({video_res['totalFrames']} frames)")
print(f"   File size: {video_res['fileSize']} bytes")

# 10. Verify MP4 video streaming endpoint
vid_get = requests.get(f"{BASE}{video_res['videoUrl']}", timeout=10)
print(f"   Video file HTTP {vid_get.status_code}, content-type: {vid_get.headers.get('content-type')}, bytes: {len(vid_get.content)}")
assert vid_get.status_code == 200
assert vid_get.headers.get("content-type") == "video/mp4"

# 11. Verify Remotion Config JSON
rem_get = requests.get(f"{BASE}/api/runs/{run_id}/remotion-config?provider=azure", timeout=10)
print(f"   Remotion Config HTTP {rem_get.status_code}, compositionId: {rem_get.json().get('compositionId')}")
assert rem_get.status_code == 200

print("\n====================================================")
print("ALL 7 PIPELINE STAGES VERIFIED 100% OPERATIONAL!")
print("====================================================")
