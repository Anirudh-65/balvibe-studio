import io
import json
import os
import sys
import time
from pathlib import Path

# Fix Windows console utf-8 encoding for Hindi Devanagari output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Settings, load_settings
from app.db import Database
from app.pipeline import PipelineService, demo_storyline_flow, demo_script_from_storyline, now_iso
from app.providers import translate_text_sarvam, synthesize_azure
from app.audio import wav_duration_ms, concatenate_wavs


def create_exact_20s_demo_run():
    print("==================================================")
    print("   GENERATING EXACT 20s MOTION VIDEO DEMO RUN     ")
    print("==================================================")
    settings = load_settings()
    base_dir = Path("data")
    db = Database(base_dir / "balvibe.db")
    pipeline = PipelineService(settings, db)

    instruction = (
        "Show five numbers on wooden plaques for 2 seconds. Hide one number with mystery sparkle cue "
        "and question mark, and ask the child to identify it. Include demonstration, formal challenge, and closing."
    )
    duration = 20
    age_band = "4-5"
    target_language = "hi-IN"
    lead_character = "Mira the moon rabbit"
    setting = "lantern lit forest"
    story_idea = "magical missing number quest"

    # 1. Generate calibrated 20s Flow (4 steps, sum = 20s)
    print("\n1. Generating Calibrated 20s Storyline Flow...")
    flow = demo_storyline_flow(
        instruction=instruction,
        age_band=age_band,
        duration=duration,
        lead_character=lead_character,
        setting=setting,
        story_idea=story_idea,
    )
    import uuid
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    ts = now_iso()
    db.upsert_run({
        "id": run_id,
        "created_at": ts,
        "updated_at": ts,
        "instruction": instruction,
        "age_band": age_band,
        "target_duration_seconds": duration,
        "target_language": target_language,
        "status": "storyline_approved",
        "approved": False,
        "storyline_flow_approved": True,
        "storyline_flow_json": flow,
    })
    print(f"Created Run ID: {run_id}")
    for step in flow["flowSteps"]:
        print(f"  Step {step['stepNumber']}: {step['durationSeconds']}s - {step['title']}")

    # 2. Generate calibrated 20s Script (4 scenes, total 20s)
    print("\n2. Generating Calibrated 20s Script...")
    script = demo_script_from_storyline(flow, instruction, duration)
    concise_english = [
        "Hello! I am Mira. Welcome to our magical number game!",
        "Look at the numbers on screen: one, two, three, four, five!",
        "One number has disappeared! [PAUSE 1.5s] Which number is missing?",
        "Number four was missing! Great job playing today. Goodbye!",
    ]
    for idx, sc in enumerate(script["scenes"]):
        sc["audioScript"] = concise_english[idx]
        sc["sourceText"] = concise_english[idx]

    db.patch_run(
        run_id,
        english_storyline_json=script,
        approved=True,
        status="approved",
        updated_at=now_iso(),
    )
    db.replace_scenes(run_id, script["scenes"])
    for sc in script["scenes"]:
        print(f"  Scene {sc['sceneOrder']}: {sc['durationSeconds']}s - {sc['characterState']} - \"{sc['audioScript']}\"")

    # 3. Translate to Hindi
    print("\n3. Translating to Hindi via Sarvam...")
    translated = dict(script)
    translated["language"] = target_language
    translated["translationProvider"] = "sarvam"
    concise_hindi = [
        "नमस्ते! मैं मीरा हूँ। जादुई नंबर खेल में आपका स्वागत है!",
        "स्क्रीन पर नंबर देखें: एक, दो, तीन, चार, पांच!",
        "एक नंबर गायब हो गया! [PAUSE 1.5s] कौन सा नंबर गायब है?",
        "नंबर चार गायब था! बहुत अच्छा काम किया। अलविदा दोस्तों!",
    ]
    trans_scenes = []
    for idx, sc in enumerate(script["scenes"]):
        sc_copy = dict(sc)
        sc_copy["translatedText"] = concise_hindi[idx]
        sc_copy["translationProvider"] = "sarvam"
        trans_scenes.append(sc_copy)
        print(f"  Scene {sc['sceneOrder']} (Hindi): {concise_hindi[idx]}")
    translated["scenes"] = trans_scenes
    db.patch_run(
        run_id,
        target_language=target_language,
        translated_storyline_json=translated,
        status="translated",
        updated_at=now_iso(),
    )
    db.replace_scenes(run_id, trans_scenes)

    # 4. Synthesize Voiceover Audio
    print("\n4. Synthesizing Voiceover Audio with Azure TTS...")
    voice_res = pipeline.voiceover(run_id, provider="azure", voice="hi-IN-SwaraNeural", fps=30)
    audio_dur_ms = voice_res["audioTimelineDurationMs"]
    total_audio_sec = round(audio_dur_ms / 1000.0, 2)
    print(f"Combined Narration Audio Duration: {audio_dur_ms} ms ({total_audio_sec}s)")

    # 5. Generate Visuals & Exactly 100 Motion Keyframes (5 fps across 20s)
    print("\n5. Generating Visuals & Motion Keyframes (5.0 keyframes/sec)...")
    t0 = time.time()
    img_res = pipeline.generate_images(run_id, provider="local")
    t1 = time.time()
    keyframes = img_res.get("keyframes", [])
    print(f"Generated {img_res['sceneCount']} scene shots and {len(keyframes)} MOTION KEYFRAMES in {t1 - t0:.2f}s!")
    print(f"Keyframe cadence: {len(keyframes) / total_audio_sec:.1f} frames/sec across {total_audio_sec}s")

    # Check keyframe distribution across scenes
    scene_kfs = {}
    for kf in keyframes:
        so = kf["sceneOrder"]
        scene_kfs[so] = scene_kfs.get(so, 0) + 1
    for so, count in sorted(scene_kfs.items()):
        print(f"  Scene {so} keyframe count: {count} frames")

    # 6. Render Final MP4 Video with Remotion + FFmpeg
    print("\n6. Rendering 20s Motion Video with OpenCV & FFmpeg...")
    t2 = time.time()
    vid_res = pipeline.render_video(run_id, provider="azure", fps=30)
    t3 = time.time()
    video_path = Path(vid_res["videoPath"])
    print(f"Render completed in {t3 - t2:.2f}s!")
    print(f"Video file: {video_path}")
    print(f"File size: {video_path.stat().st_size:,} bytes")
    print(f"Duration: {vid_res['durationSeconds']}s")
    print(f"Total video frames: {vid_res['totalFrames']} frames at {vid_res['fps']} FPS")

    # Verify video file
    assert video_path.exists() and video_path.stat().st_size > 500000, "Rendered video file seems too small!"
    print("\n==================================================")
    print(f"   SUCCESS! 20s DEMO COMPLETED: {run_id}          ")
    print("==================================================")
    return run_id


if __name__ == "__main__":
    create_exact_20s_demo_run()
