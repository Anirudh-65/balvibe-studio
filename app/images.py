from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .config import Settings
from .storage import StorageBackend
from .motion import MotionKeyframeEngine


class BaseImageProvider(ABC):
    @abstractmethod
    def generate_scene_images(
        self,
        scenes: list[dict[str, Any]],
        run_id: str,
        storage: StorageBackend,
        setting: str,
        character_name: str,
    ) -> list[dict[str, Any]]:
        """Generate or assign images for each scene and return enriched scene records."""
        pass


class LocalSampleImageProvider(BaseImageProvider):
    """Local image provider using high-fidelity pre-rendered cinematic scene visuals

    with procedural styling, Gemini-ready prompts, and 80-120 high-cadence motion keyframes.
    """

    def __init__(self, sample_assets_dir: Path):
        self.sample_assets_dir = sample_assets_dir.resolve()
        self.motion_engine = MotionKeyframeEngine(self.sample_assets_dir)

    def generate_keyframes(
        self,
        scenes: list[dict[str, Any]],
        run_id: str,
        storage: StorageBackend,
        keyframe_fps: int = 5,
        width: int = 1280,
        height: int = 720,
    ) -> list[dict[str, Any]]:
        return self.motion_engine.generate_keyframes_for_run(
            run_id=run_id,
            scenes=scenes,
            storage=storage,
            keyframe_fps=keyframe_fps,
            width=width,
            height=height,
        )

    def generate_scene_images(
        self,
        scenes: list[dict[str, Any]],
        run_id: str,
        storage: StorageBackend,
        setting: str,
        character_name: str,
    ) -> list[dict[str, Any]]:
        enriched_scenes: list[dict[str, Any]] = []
        sample_files = sorted(list(self.sample_assets_dir.glob("*.jpg")))
        total_samples = len(sample_files)

        for idx, scene in enumerate(scenes):
            order = int(scene.get("sceneOrder", idx + 1))
            char_state = scene.get("characterState", "friendly")
            asset_tag = scene.get("visualAssetTag", f"scene_{order}")
            script_text = scene.get("audioScript", "")
            trial_meta = scene.get("trial")

            # Build Gemini Imagen / Nano Banana prompt
            trial_desc = ""
            if trial_meta:
                phase = trial_meta.get("phase", "trial")
                missing = trial_meta.get("missingNumber")
                if missing is not None:
                    trial_desc = f" Displaying numbers on wooden plaques with number {missing} hidden, glowing mystery question mark."
                else:
                    trial_desc = f" Displaying numbers clearly on wooden plaques for {phase} phase."

            prompt = (
                f"3D Pixar style digital art of {character_name} in a {setting}. "
                f"Pose and action: {char_state}. {trial_desc} "
                f"Story context: {script_text[:120]}. Cinematic soft lighting, high-detail educational children video."
            )

            filename = f"scene_{order:03d}_{asset_tag}.jpg"
            relative_path = f"runs/{run_id}/images/{filename}"

            # Pick matching sample image or procedural fallback
            if total_samples > 0:
                sample_index = (order - 1) % total_samples
                source_image_path = sample_files[sample_index]
                image_bytes = source_image_path.read_bytes()
            else:
                image_bytes = self._generate_fallback_image(order, character_name, setting, char_state)

            storage_path = storage.store_bytes(relative_path, image_bytes)
            public_url = f"/api/runs/{run_id}/images/{filename}"

            scene_copy = dict(scene)
            scene_copy["imageFileName"] = filename
            scene_copy["imageUrl"] = public_url
            scene_copy["imagePrompt"] = prompt
            scene_copy["imageProvider"] = "local_sample"
            scene_copy["imageStoragePath"] = str(storage_path)
            enriched_scenes.append(scene_copy)

        return enriched_scenes

    def _generate_fallback_image(
        self, order: int, character_name: str, setting: str, character_state: str
    ) -> bytes:
        img = Image.new("RGB", (1280, 720), color=(30, 41, 59))
        draw = ImageDraw.Draw(img)
        draw.rectangle([60, 60, 1220, 660], outline=(99, 102, 241), width=4)
        draw.text((100, 100), f"Scene {order:02d} - {setting}", fill=(248, 250, 252))
        draw.text((100, 160), f"Character: {character_name} ({character_state})", fill=(148, 163, 184))
        import io
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()


class GeminiImageProvider(BaseImageProvider):
    """Google Gemini Imagen / Nano Banana API provider.

    Activates as soon as GEMINI_API_KEY is configured in .env.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_scene_images(
        self,
        scenes: list[dict[str, Any]],
        run_id: str,
        storage: StorageBackend,
        setting: str,
        character_name: str,
    ) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. Please add GEMINI_API_KEY in .env or choose the Local Sample provider."
            )
        # Placeholder for live Gemini Imagen endpoint
        # e.g. requests.post("https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict", ...)
        raise NotImplementedError("Live Gemini Imagen API calls will be made when GEMINI_API_KEY is enabled.")
