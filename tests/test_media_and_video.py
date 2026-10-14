import tempfile
from pathlib import Path
import unittest

from app.storage import LocalFilesystemStorage
from app.images import LocalSampleImageProvider
from app.video import VideoCompositionService
from app.audio import tone_wav


class MediaAndVideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.storage = LocalFilesystemStorage(self.root)
        self.sample_dir = Path("data/sample_images").resolve()
        self.image_provider = LocalSampleImageProvider(self.sample_dir)
        self.video_service = VideoCompositionService(self.storage)

    def tearDown(self):
        self.tmp.cleanup()

    def test_image_generation_and_storage(self):
        scenes = [
            {"sceneOrder": 1, "audioScript": "Hello welcome to the forest", "characterState": "waving", "visualAssetTag": "intro"},
            {"sceneOrder": 2, "audioScript": "Look at the numbers", "characterState": "pointing", "visualAssetTag": "practice"},
        ]
        enriched = self.image_provider.generate_scene_images(scenes, "run-test123456", self.storage, "lantern lit forest", "Mira")
        self.assertEqual(len(enriched), 2)
        self.assertTrue(enriched[0]["imageUrl"].startswith("/api/runs/run-test123456/images/"))
        self.assertTrue(Path(enriched[0]["imageStoragePath"]).exists())
        self.assertTrue("Gemini" in enriched[0]["imagePrompt"] or "Mira" in enriched[0]["imagePrompt"])

    def test_video_composition_with_ffmpeg(self):
        scenes = [
            {
                "sceneOrder": 1,
                "characterName": "Mira",
                "audioScript": "Welcome to the game",
                "startTimeMs": 0,
                "endTimeMs": 1500,
                "audioDurationMs": 1500,
                "imageStoragePath": str(self.sample_dir / "scene_001_intro.jpg"),
            },
            {
                "sceneOrder": 2,
                "characterName": "Mira",
                "audioScript": "Now find the missing number",
                "startTimeMs": 1500,
                "endTimeMs": 3000,
                "audioDurationMs": 1500,
                "imageStoragePath": str(self.sample_dir / "scene_002_practice.jpg"),
            },
        ]
        wav_data = tone_wav(3.0, 220.0)
        audio_path = self.root / "combined.wav"
        audio_path.write_bytes(wav_data)

        res = self.video_service.render_video("run-test123456", scenes, audio_path, provider="azure", fps=30)
        self.assertEqual(res["runId"], "run-test123456")
        self.assertTrue(Path(res["videoPath"]).exists())
        self.assertTrue(res["fileSize"] > 1000)
        self.assertEqual(res["videoUrl"], "/api/runs/run-test123456/video/azure")

    def test_motion_keyframes_generation_and_video_interpolation(self):
        scenes = [
            {
                "sceneOrder": 1,
                "characterName": "Mira",
                "audioScript": "Welcome to our 20s game",
                "startTimeMs": 0,
                "endTimeMs": 10000,
                "audioDurationMs": 10000,
                "characterState": "waving",
            },
            {
                "sceneOrder": 2,
                "characterName": "Mira",
                "audioScript": "Watch the mystery card disappear",
                "startTimeMs": 10000,
                "endTimeMs": 20000,
                "audioDurationMs": 10000,
                "characterState": "attentive",
            },
        ]
        keyframes = self.image_provider.generate_keyframes(scenes, "run-test-kf", self.storage, keyframe_fps=4)
        # Should be between 80 and 120 keyframes
        self.assertGreaterEqual(len(keyframes), 80)
        self.assertLessEqual(len(keyframes), 120)
        self.assertTrue(Path(keyframes[0]["storagePath"]).exists())
        self.assertEqual(keyframes[0]["keyframeIndex"], 1)

        wav_data = tone_wav(20.0, 220.0)
        audio_path = self.root / "combined_20s.wav"
        audio_path.write_bytes(wav_data)

        res = self.video_service.render_video(
            "run-test-kf", scenes, audio_path, provider="azure", fps=30, keyframes=keyframes
        )
        self.assertTrue(Path(res["videoPath"]).exists())
        self.assertGreater(res["fileSize"], 50000)
        self.assertEqual(res["totalFrames"], 600)


if __name__ == "__main__":
    unittest.main()
