from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.models import Handedness, Stroke, View
from app.pipeline import AnalysisPipeline
from app.pose.estimator import MediaPipePoseEstimator, SyntheticPoseEstimator

app = FastAPI(title="TennisIQ Analysis", version="0.1.0")

_USE_SYNTHETIC = os.getenv("TENNISIQ_SYNTHETIC_POSE", "").lower() in {"1", "true", "yes"}


def _pipeline() -> AnalysisPipeline:
    if _USE_SYNTHETIC:
        return AnalysisPipeline(estimator=SyntheticPoseEstimator())
    return AnalysisPipeline(estimator=MediaPipePoseEstimator())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    video: UploadFile = File(...),
    stroke: str = Form("forehand"),
    handedness: str = Form("right"),
    view: str = Form("side"),
    allow_synthetic_fallback: bool = Form(False),
):
    try:
        stroke_e = Stroke(stroke)
        hand_e = Handedness(handedness)
        view_e = View(view)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    suffix = Path(video.filename or "clip.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await video.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty video upload")
        tmp.write(content)
        video_path = Path(tmp.name)

    overlay_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    overlay_path = Path(overlay_tmp.name)
    overlay_tmp.close()

    try:
        pipe = _pipeline()
        # When forced synthetic mode, ignore the video pixels for pose.
        if _USE_SYNTHETIC:
            pipe.estimator = SyntheticPoseEstimator(stroke=stroke_e, handedness=hand_e)
        result, overlay = pipe.analyze(
            video_path=video_path,
            stroke=stroke_e,
            handedness=hand_e,
            view=view_e,
            overlay_path=overlay_path,
            use_synthetic_if_blank=allow_synthetic_fallback or _USE_SYNTHETIC,
        )
    finally:
        video_path.unlink(missing_ok=True)

    payload = result.model_dump()
    ready = (
        overlay is not None
        and overlay.exists()
        and overlay.stat().st_size > 500
        and result.status == "ok"
    )
    if ready:
        token = overlay.name
        _OVERLAYS[token] = overlay
        payload["overlay_ready"] = True
        payload["overlay_token"] = token
    else:
        payload["overlay_ready"] = False
        if overlay_path.exists() and overlay_path.stat().st_size <= 500:
            overlay_path.unlink(missing_ok=True)

    return JSONResponse(payload)


_OVERLAYS: dict[str, Path] = {}


@app.get("/overlay/{token}")
def get_overlay(token: str):
    path = _OVERLAYS.get(token)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path, media_type="video/mp4", filename="overlay.mp4")
