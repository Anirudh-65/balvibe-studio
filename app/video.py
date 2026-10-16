from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .storage import StorageBackend


def get_default_font(size: int = 24) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try Windows system fonts for Unicode/Hindi/Indic support, fallback to default
    candidates = [
        r"C:\Windows\Fonts\Nirmala.ttc",
        r"C:\Windows\Fonts\ARIALUNI.ttf",
        r"C:\Windows\Fonts\mangal.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_bold_font(size: int = 28) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\Nirmala.ttc",
        r"C:\Windows\Fonts\segouib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


class VideoCompositionService:
    """Remotion + FFmpeg video composition engine for sequencing motion keyframes,

    character gestures, animated stimuli, and synchronized audio into an MP4 video.
    """

    def __init__(self, storage: StorageBackend):
        self.storage = storage
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def render_video(
        self,
        run_id: str,
        scenes: list[dict[str, Any]],
        combined_audio_path: Path,
        provider: str,
        fps: int = 30,
        width: int = 1280,
        height: int = 720,
        keyframes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not scenes:
            raise ValueError("No scenes available for video render.")
        if not combined_audio_path.exists():
            raise FileNotFoundError(f"Combined audio not found: {combined_audio_path}")

        # Compute timeline
        total_duration_ms = max(int(scenes[-1].get("endTimeMs", 0)), 1000)
        total_frames = max(int(total_duration_ms * fps / 1000), 30)

        # 1. Generate Remotion-compatible composition descriptor JSON
        remotion_config = self._build_remotion_config(run_id, scenes, combined_audio_path, provider, fps, width, height, keyframes=keyframes)
        remotion_filename = f"remotion_composition_{provider}.json"
        remotion_rel = f"runs/{run_id}/video/{remotion_filename}"
        remotion_path = self.storage.store_bytes(
            remotion_rel,
            json.dumps(remotion_config, ensure_ascii=False, indent=2).encode("utf-8"),
        )

        # 2. Render video frames using OpenCV & Pillow
        temp_dir = tempfile.TemporaryDirectory()
        temp_video_raw = Path(temp_dir.name) / "temp_video.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(temp_video_raw), fourcc, fps, (width, height))

        font_sub = get_default_font(size=26)
        font_badge = get_bold_font(size=20)
        font_num = get_bold_font(size=24)

        # Keep keyframes on disk and load only the frame currently being
        # encoded. Preloading every 1280x720 image can exceed small-host
        # memory limits when a run contains 80-120 keyframes.
        keyframe_paths: list[Path] = []
        if keyframes:
            for kf in keyframes:
                kf_path = kf.get("storagePath")
                if kf_path and os.path.exists(kf_path):
                    keyframe_paths.append(Path(kf_path))
        loaded_keyframe: Image.Image | None = None
        loaded_keyframe_index: int | None = None

        # Fallback pre-load scene images
        loaded_images: dict[int, Image.Image] = {}
        for sc in scenes:
            order = sc["sceneOrder"]
            img_path = sc.get("imageStoragePath")
            if img_path and os.path.exists(img_path):
                try:
                    loaded_images[order] = Image.open(img_path).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
                except Exception:
                    loaded_images[order] = self._create_gradient_slide(width, height, sc)
            else:
                loaded_images[order] = self._create_gradient_slide(width, height, sc)

        tot_sec = total_duration_ms / 1000.0

        # Render frame by frame
        for frame_idx in range(total_frames):
            current_time_ms = frame_idx * 1000 / fps
            cur_sec = current_time_ms / 1000.0

            # Find active scene
            active_scene = scenes[0]
            for sc in scenes:
                if sc["startTimeMs"] <= current_time_ms <= sc["endTimeMs"]:
                    active_scene = sc
                    break
                elif current_time_ms > sc["endTimeMs"]:
                    active_scene = sc

            scene_order = active_scene["sceneOrder"]

            # Direct keyframe sampling for 100% crisp, razor-sharp video frames (zero ghosting)
            if keyframe_paths:
                kf_pos = cur_sec * (len(keyframe_paths) - 1) / max(tot_sec, 0.001)
                kf_idx = max(0, min(len(keyframe_paths) - 1, int(round(kf_pos))))
                if kf_idx != loaded_keyframe_index:
                    with Image.open(keyframe_paths[kf_idx]) as keyframe_image:
                        loaded_keyframe = keyframe_image.convert("RGB").resize(
                            (width, height), Image.Resampling.LANCZOS
                        )
                    loaded_keyframe_index = kf_idx
                if loaded_keyframe is None:
                    raise RuntimeError("Unable to load the selected video keyframe.")
                base_img = loaded_keyframe.copy()
            else:
                base_img = loaded_images.get(scene_order, loaded_images[scenes[0]["sceneOrder"]]).copy()

            # Only draw HUD chips and dark subtitle box if fallback slides are used without keyframes
            if not keyframe_paths:
                draw = ImageDraw.Draw(base_img, "RGBA")

                # A. Top Header Chips
                # Scene Chip (left)
                draw.rounded_rectangle([32, 28, 220, 68], radius=16, fill=(15, 23, 42, 220), outline=(99, 102, 241, 200), width=2)
                draw.text((46, 36), f"SCENE {scene_order:02d} / {len(scenes):02d}", fill=(248, 250, 252), font=font_badge)

                # Timer Chip (right)
                timer_text = f"{int(cur_sec//60):02d}:{int(cur_sec%60):02d} / {int(tot_sec//60):02d}:{int(tot_sec%60):02d}"
                draw.rounded_rectangle([width - 240, 28, width - 32, 68], radius=16, fill=(15, 23, 42, 220), outline=(56, 189, 248, 200), width=2)
                draw.text((width - 222, 36), timer_text, fill=(56, 189, 248), font=font_badge)

                # B. Trial overlay (if stimulus phase is active)
                trial = active_scene.get("trial")
                if trial:
                    phase_name = str(trial.get("phase", "trial")).upper()
                    draw.rounded_rectangle([width // 2 - 130, 28, width // 2 + 130, 68], radius=16, fill=(245, 158, 11, 230))
                    draw.text((width // 2 - 110, 36), f"TRIAL · {phase_name}", fill=(15, 23, 42), font=font_badge)

                # C. Lower-Third Synced Subtitle Banner
                subtitle_text = str(active_scene.get("translatedText") or active_scene.get("audioScript") or "").strip()
                clean_subtitle = " ".join([w for w in subtitle_text.split() if not w.startswith("[PAUSE") and not w.endswith("]")])

                speaker_name = active_scene.get("characterName", "Companion")
                sub_y = height - 120

                draw.rounded_rectangle([60, sub_y, width - 60, height - 32], radius=18, fill=(15, 23, 42, 230), outline=(255, 255, 255, 60), width=1)
                draw.rounded_rectangle([76, sub_y + 12, 210, sub_y + 44], radius=10, fill=(99, 102, 241, 230))
                draw.text((90, sub_y + 16), speaker_name, fill=(255, 255, 255), font=font_badge)

                max_chars = 62
                display_sub = clean_subtitle if len(clean_subtitle) <= max_chars else clean_subtitle[:max_chars] + "..."
                draw.text((230, sub_y + 16), display_sub, fill=(248, 250, 252), font=font_sub)

            # Convert PIL RGB to OpenCV BGR
            cv_frame = cv2.cvtColor(np.array(base_img), cv2.COLOR_RGB2BGR)
            writer.write(cv_frame)

        writer.release()

        # 3. Mux video with narration audio using FFmpeg
        final_filename = f"video_{provider}.mp4"
        final_rel = f"runs/{run_id}/video/{final_filename}"
        final_video_path = (self.storage.base_dir / final_rel).resolve() if hasattr(self.storage, "base_dir") else Path(temp_dir.name) / final_filename
        final_video_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", str(temp_video_raw),
            "-i", str(combined_audio_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(final_video_path),
        ]

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        temp_dir.cleanup()

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg muxing failed: {proc.stderr.decode('utf-8', errors='ignore')[:600]}")

        video_url = f"/api/runs/{run_id}/video/{provider}"
        remotion_url = f"/api/runs/{run_id}/remotion-config"

        return {
            "runId": run_id,
            "provider": provider,
            "videoPath": str(final_video_path),
            "videoUrl": video_url,
            "durationSeconds": round(total_duration_ms / 1000.0, 2),
            "totalFrames": total_frames,
            "fps": fps,
            "width": width,
            "height": height,
            "remotionConfigUrl": remotion_url,
            "fileSize": final_video_path.stat().st_size,
        }

    def _create_gradient_slide(self, width: int, height: int, scene: dict[str, Any]) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        font_large = get_bold_font(38)
        font_med = get_default_font(24)
        draw.text((80, 220), f"Scene {scene.get('sceneOrder', 1):02d}", fill=(99, 102, 241), font=font_large)
        draw.text((80, 280), str(scene.get("setting", "Educational Experiment Scene")), fill=(248, 250, 252), font=font_large)
        draw.text((80, 340), f"Character: {scene.get('characterName', 'Host')} ({scene.get('characterState', 'active')})", fill=(148, 163, 184), font=font_med)
        return img

    def _build_remotion_config(
        self,
        run_id: str,
        scenes: list[dict[str, Any]],
        audio_path: Path,
        provider: str,
        fps: int,
        width: int,
        height: int,
        keyframes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "compositionId": f"BalVibeVideo-{run_id}",
            "fps": fps,
            "width": width,
            "height": height,
            "durationInFrames": int(scenes[-1]["endTimeMs"] * fps / 1000),
            "audioTrack": {
                "src": f"/api/runs/{run_id}/audio/{provider}/{audio_path.name}",
                "durationMs": scenes[-1]["endTimeMs"],
            },
            "scenes": [
                {
                    "sceneNumber": sc["sceneOrder"],
                    "imageSrc": sc.get("imageUrl"),
                    "startFrame": sc.get("startFrame"),
                    "endFrame": sc.get("endFrameExclusive"),
                    "durationInFrames": sc.get("totalFrames"),
                    "speaker": sc.get("characterName"),
                    "subtitle": sc.get("translatedText") or sc.get("audioScript"),
                    "trial": sc.get("trial"),
                }
                for sc in scenes
            ],
            "keyframes": [
                {
                    "keyframeIndex": kf["keyframeIndex"],
                    "timeSeconds": kf["timeSeconds"],
                    "src": kf.get("url"),
                    "sceneOrder": kf.get("sceneOrder"),
                }
                for kf in (keyframes or [])
            ],
            "props": {
                "theme": "educational-indic",
                "showSubtitles": True,
                "showSceneBadge": True,
                "motionInterpolation": True,
            },
        }
