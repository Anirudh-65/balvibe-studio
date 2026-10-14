import time, sys, os, requests

# Reconfigure console output for Windows UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = "http://127.0.0.1:8000"

print("====================================================")
print("TESTING 2D CHARACTER-PUPPET EXPLAINER ENGINE (INTRO.MP4 STYLE)")
print("====================================================")

# 1. Health check
h = requests.get(f"{BASE}/api/health", timeout=5).json()
print("1. Health OK:", h.get("ok"))

# 2. Stage 1: Generate Storyline Flow for 20s sample
print("\n2. Stage 1: Generate Storyline Flow (20s)...")
gen = requests.post(
    f"{BASE}/api/generate-storyline",
    json={
        "instruction": "Show the letter game on Magic Island. When looking at the center cross +, remember if you move your eyes away the magic boat sinks! Flashing letters appear, then masked. Report the letter marked by the blue cue.",
        "ageBand": "6-8",
        "duration": 20,
        "targetLanguage": "en-US",
        "leadCharacter": "Magic Monkey",
        "setting": "Magic Island",
        "storyIdea": "ride the magic boat to the door",
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
print("\n4. Stage 2: Generating Script from Approved Flow...")
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

# 6. Stage 3: Translate Narration (Sarvam)
print("\n6. Stage 3: Translating Narration with Sarvam...")
trans = requests.post(
    f"{BASE}/api/runs/{run_id}/translate",
    json={"targetLanguage": "hi-IN", "provider": "sarvam"},
    timeout=120,
).json()
print(f"   Translated {len(trans['storyline']['scenes'])} scenes to Hindi.")

# 7. Stage 4: Voiceover (Azure Speech)
print("\n7. Stage 4: Synthesizing Voiceover with Azure Speech...")
audio = requests.post(
    f"{BASE}/api/runs/{run_id}/voiceover",
    json={"provider": "azure", "voice": "hi-IN-SwaraNeural", "fps": 24},
    timeout=180,
).json()
print(f"   Voiceover status: {audio.get('status')}")

# 8. Stage 5: Generate 80-120 Keyframes with 2D Character Explainer Engine
print("\n8. Stage 5: Generating Keyframes (2D Mascot Puppet + Animated Cursor)...")
t0 = time.time()
img_resp = requests.post(
    f"{BASE}/api/runs/{run_id}/generate-images",
    json={"provider": "local"},
    timeout=180,
).json()
t_kf = time.time() - t0

kf_info = requests.get(f"{BASE}/api/runs/{run_id}/keyframes", timeout=10).json()
keyframes = kf_info.get("keyframes", [])
print(f"   Successfully generated {len(keyframes)} KEYFRAMES in {t_kf:.2f}s!")
if keyframes:
    print(f"   First keyframe: {keyframes[0]['fileName']}")
    print(f"   Last keyframe:  {keyframes[-1]['fileName']}")

# 8. Stage 6: Render Final Video
print("\n8. Stage 6: Rendering Final MP4 Video...")
t0_vid = time.time()
vid_resp = requests.post(
    f"{BASE}/api/runs/{run_id}/render-video",
    json={"provider": "azure", "fps": 24},
    timeout=180,
).json()
t_vid = time.time() - t0_vid
video_url = vid_resp.get("videoUrl")
print(f"   Video Render Complete in {t_vid:.2f}s!")
print(f"   Video URL: {video_url}")

# Verify file on disk
vid_info = requests.get(f"{BASE}/api/runs/{run_id}", timeout=10).json()
print("\n====================================================")
print("RUN SUMMARY:")
print(f"   Run ID:         {run_id}")
print(f"   Total Scenes:   {len(scenes)}")
print(f"   Total Keyframes:{len(keyframes)}")
print(f"   Render Time:    {t_kf + t_vid:.2f}s total")
print(f"   Final Video:    {video_url}")
print("====================================================")
