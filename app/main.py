from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from .config import load_settings
from .db import Database
from .pipeline import PipelineService
from .providers import provider_config

settings = load_settings()
db = Database(settings.data_dir / "balvibe.db")
pipeline = PipelineService(settings, db)

app = FastAPI(title="BalVibe Studio", version="1.0.0")


class GenerateRequest(BaseModel):
    instruction: str = Field(min_length=10, max_length=20000)
    ageBand: str = "6-8"
    duration: int = Field(default=20, ge=20, le=3600)
    targetLanguage: str = "hi-IN"
    leadCharacter: str | None = None
    setting: str | None = None
    storyIdea: str | None = None


class StorylineFlowRequest(BaseModel):
    storylineFlow: dict[str, Any]


class StorylineRequest(BaseModel):
    storyline: dict[str, Any]


class TranslateRequest(BaseModel):
    targetLanguage: str = "hi-IN"
    provider: str = "sarvam"


class VoiceoverRequest(BaseModel):
    provider: str
    voice: str
    fps: int = 30


class ImageGenRequest(BaseModel):
    provider: str = "local"


class VideoRenderRequest(BaseModel):
    provider: str | None = None
    fps: int = 30


def api_error(exc: Exception) -> HTTPException:
    import traceback
    traceback.print_exc()
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail="Run not found.")
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail="Audio file not found.")
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Server error: {exc}")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "demoMode": settings.demo_mode,
        "providers": {
            "groqConfigured": bool(settings.groq_api_key),
            "sarvamConfigured": bool(settings.sarvam_api_key),
            "bhashiniConfigured": bool(settings.bhashini_user_id and settings.bhashini_api_key),
            "azureConfigured": bool(settings.azure_speech_key),
        },
        "database": str(db.path),
        "dataDirectory": str(settings.data_dir),
    }


@app.get("/api/config")
def config() -> dict[str, Any]:
    return provider_config() | {"demoMode": settings.demo_mode}


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return db.list_runs()


# Stage 1: Generate gamified storyline flow from researcher instructions
@app.post("/api/generate-storyline")
def generate_storyline(req: GenerateRequest) -> dict[str, Any]:
    try:
        return pipeline.create_storyline_run(
            req.instruction,
            req.ageBand,
            req.duration,
            req.targetLanguage,
            lead_character=req.leadCharacter,
            setting=req.setting,
            story_idea=req.storyIdea,
        )
    except Exception as exc:
        raise api_error(exc)


# Save edits to the gamified storyline flow
@app.put("/api/runs/{run_id}/storyline-flow")
def save_storyline_flow(run_id: str, req: StorylineFlowRequest) -> dict[str, Any]:
    try:
        return {"runId": run_id, "storylineFlow": pipeline.save_storyline_flow(run_id, req.storylineFlow)}
    except Exception as exc:
        raise api_error(exc)


# Approve and lock the gamified storyline flow (required before script generation)
@app.post("/api/runs/{run_id}/approve-storyline")
def approve_storyline_flow(run_id: str, req: StorylineFlowRequest | None = None) -> dict[str, Any]:
    try:
        return pipeline.approve_storyline_flow(run_id, req.storylineFlow if req else None)
    except Exception as exc:
        raise api_error(exc)


# Unlock storyline flow for editing
@app.post("/api/runs/{run_id}/unlock-storyline")
def unlock_storyline_flow(run_id: str) -> dict[str, Any]:
    try:
        return pipeline.unlock_storyline_flow(run_id)
    except Exception as exc:
        raise api_error(exc)


# Stage 2: Generate script & dialogues from the approved storyline flow ONLY
@app.post("/api/runs/{run_id}/generate-script")
def generate_script_from_flow(run_id: str) -> dict[str, Any]:
    try:
        return pipeline.generate_script(run_id)
    except Exception as exc:
        raise api_error(exc)


# Legacy / backwards-compatible full generation endpoint
@app.post("/api/generate-script")
def generate(req: GenerateRequest) -> dict[str, Any]:
    try:
        return pipeline.create_run(
            req.instruction,
            req.ageBand,
            req.duration,
            req.targetLanguage,
            lead_character=req.leadCharacter,
            setting=req.setting,
            story_idea=req.storyIdea,
        )
    except Exception as exc:
        raise api_error(exc)


# Save edits to the scene script & dialogues
@app.put("/api/runs/{run_id}/storyline")
def save_storyline(run_id: str, req: StorylineRequest) -> dict[str, Any]:
    try:
        return {"runId": run_id, "storyline": pipeline.save_storyline(run_id, req.storyline)}
    except Exception as exc:
        raise api_error(exc)


# Approve and lock the scene script & dialogues (required before translation)
@app.post("/api/runs/{run_id}/approve")
def approve(run_id: str, req: StorylineRequest | None = None) -> dict[str, Any]:
    try:
        return pipeline.approve(run_id, req.storyline if req else None)
    except Exception as exc:
        raise api_error(exc)


# Unlock script for editing
@app.post("/api/runs/{run_id}/unlock-script")
def unlock_script(run_id: str) -> dict[str, Any]:
    try:
        return pipeline.unlock_script(run_id)
    except Exception as exc:
        raise api_error(exc)


# Stage 3: Translate approved script narration
@app.post("/api/runs/{run_id}/translate")
def translate(run_id: str, req: TranslateRequest) -> dict[str, Any]:
    try:
        return pipeline.translate(run_id, req.targetLanguage, req.provider)
    except Exception as exc:
        raise api_error(exc)


# Stage 4: Synthesize voiceover audio
@app.post("/api/runs/{run_id}/voiceover")
def voiceover(run_id: str, req: VoiceoverRequest) -> dict[str, Any]:
    try:
        return pipeline.voiceover(run_id, req.provider, req.voice, req.fps)
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    try:
        return pipeline.get_run_public(run_id)
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/dataset")
def get_dataset(run_id: str) -> JSONResponse:
    try:
        run = pipeline.get_run_public(run_id)
        if not run["dataset"]:
            raise ValueError("Voiceover dataset has not been generated yet.")
        return JSONResponse(run["dataset"], headers={"Content-Disposition": f'attachment; filename="{run_id}-dataset.json"'})
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/audio/{provider}/{filename}")
def audio(run_id: str, provider: str, filename: str) -> FileResponse:
    try:
        return FileResponse(pipeline.audio_path(run_id, provider, filename), media_type="audio/wav", filename=filename)
    except Exception as exc:
        raise api_error(exc)


@app.post("/api/runs/{run_id}/generate-images")
def generate_images(run_id: str, req: ImageGenRequest | None = None) -> dict[str, Any]:
    try:
        prov = req.provider if req else "local"
        return pipeline.generate_images(run_id, provider=prov)
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/images/{filename}")
def get_image(run_id: str, filename: str) -> FileResponse:
    try:
        return FileResponse(pipeline.image_path(run_id, filename), media_type="image/jpeg", filename=filename)
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/keyframes")
def get_keyframes(run_id: str) -> dict[str, Any]:
    try:
        kfs = pipeline.get_keyframes(run_id)
        return {"runId": run_id, "keyframeCount": len(kfs), "keyframes": kfs}
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/keyframes/{filename}")
def get_keyframe(run_id: str, filename: str) -> FileResponse:
    try:
        return FileResponse(pipeline.keyframe_path(run_id, filename), media_type="image/jpeg", filename=filename)
    except Exception as exc:
        raise api_error(exc)


@app.post("/api/runs/{run_id}/render-video")
def render_video(run_id: str, req: VideoRenderRequest | None = None) -> dict[str, Any]:
    try:
        prov = req.provider if req else None
        fps = req.fps if req else 30
        return pipeline.render_video(run_id, provider=prov, fps=fps)
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/video/{provider}")
def get_video(run_id: str, provider: str) -> FileResponse:
    try:
        return FileResponse(pipeline.video_path(run_id, provider), media_type="video/mp4", filename=f"{run_id}_{provider}.mp4")
    except Exception as exc:
        raise api_error(exc)


@app.get("/api/runs/{run_id}/remotion-config")
def get_remotion_config(run_id: str, provider: str = "azure") -> JSONResponse:
    try:
        import json
        cfg_path = pipeline.remotion_config_path(run_id, provider)
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return JSONResponse(data, headers={"Content-Disposition": f'attachment; filename="{run_id}-remotion.json"'})
    except Exception as exc:
        raise api_error(exc)


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
