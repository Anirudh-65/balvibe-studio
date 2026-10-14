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
from app.pipeline import PipelineService


def test_20s_motion_pipeline(existing_run_id: str | None = None):
    print("=== Testing 20s BalVibe Motion Pipeline ===")
    settings = load_settings()
    base_dir = Path("data")
    db = Database(base_dir / "balvibe.db")
    pipeline = PipelineService(settings, db)

    if existing_run_id:
        run_id = existing_run_id
        print(f"Resuming existing run: {run_id}")
    else:
        instruction = (
            "Show five numbers on wooden plaques for 2 seconds. Hide one number with mystery sparkle cue "
            "and question mark, and ask the child to identify it. Include demonstration, formal challenge, and closing."
        )

        # 1. Create run with 20s duration
        print("\n1. Initializing 20s Run...")
        run_res = pipeline.create_storyline_run(
            instruction=instruction,
            age_band="4-5",
            duration=20,
            target_language="hi-IN",
            lead_character="Mira the moon rabbit",
            setting="lantern lit forest",
            story_idea="magical missing number quest",
        )
        run_id = run_res["runId"]
        print(f"Created Run ID: {run_id}")

        # 2. Approve Storyline Flow
        print("\n2. Approving Storyline Flow...")
        pipeline.approve_storyline_flow(run_id)

        # 3. Generate Script
        print("\n3. Generating Script...")
        script_res = pipeline.generate_script(run_id)
        scenes = script_res["storyline"]["scenes"]
        print(f"Generated {len(scenes)} scenes:")
        for s in scenes:
            print(f"  Scene {s['sceneOrder']}: {s['durationSeconds']}s - {s['characterState']} - \"{s['audioScript'][:60]}...\"")

        # 4. Approve Script
        print("\n4. Approving Script...")
        pipeline.approve(run_id)

        # 5. Translate (Hindi)
        print("\n5. Translating to Hindi (hi-IN) via Sarvam...")
        pipeline.translate(run_id, target_language="hi-IN", provider="sarvam")

    # 6. Synthesize Voiceover (Azure)
    print("\n6. Synthesizing Voiceover (Azure hi-IN-SwaraNeural)...")
    voice_res = pipeline.voiceover(run_id, provider="azure", voice="hi-IN-SwaraNeural", fps=30)
    audio_dur_ms = voice_res["audioTimelineDurationMs"]
    print(f"Combined Audio Duration: {audio_dur_ms} ms ({audio_dur_ms / 1000.0:.2f}s)")

    # 7. Generate Visuals & 80-120 Motion Keyframes
    print("\n7. Generating Visuals & 80-120 Motion Keyframes...")
    t0 = time.time()
    img_res = pipeline.generate_images(run_id, provider="local")
    t1 = time.time()
    keyframes = img_res.get("keyframes", [])
    print(f"Generated {img_res['sceneCount']} scene shots and {len(keyframes)} MOTION KEYFRAMES in {t1 - t0:.2f}s!")

    assert len(keyframes) >= 80, f"Expected at least 80 keyframes, got {len(keyframes)}"
    print(f"Verified: {len(keyframes)} keyframes generated (target 80-120)!")

    # Check that keyframe files exist on disk
    for kf in keyframes[:5]:
        p = Path(kf["storagePath"])
        assert p.exists(), f"Keyframe file missing: {p}"
        print(f"  Checked {kf['fileName']} ({p.stat().st_size} bytes, t={kf['timeSeconds']}s)")

    # 8. Render Final MP4 Video
    print("\n8. Rendering Final Motion Video (H.264/AAC Muxing)...")
    t2 = time.time()
    vid_res = pipeline.render_video(run_id, provider="azure", fps=30)
    t3 = time.time()
    video_path = Path(vid_res["videoPath"])
    print(f"Render completed in {t3 - t2:.2f}s!")
    print(f"Video file: {video_path}")
    print(f"File size: {video_path.stat().st_size:,} bytes")
    print(f"Duration: {vid_res['durationSeconds']}s")
    print(f"Total video frames: {vid_res['totalFrames']} frames at {vid_res['fps']} FPS")

    assert video_path.exists() and video_path.stat().st_size > 500000, "Rendered video file seems too small or missing!"
    print("\nSUCCESS! 20s Motion Video with 80-120 Keyframes rendered perfectly!")
    return run_id


if __name__ == "__main__":
    existing = sys.argv[1] if len(sys.argv) > 1 else None
    test_20s_motion_pipeline(existing)
