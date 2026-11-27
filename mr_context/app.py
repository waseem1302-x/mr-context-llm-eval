"""FastAPI app: POST /evaluate, GET /health, demo UI at /.

Run: uvicorn mr_context.app:app --reload
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .llm import generate
from .scene import Scene, load_scenes
from .verify import load_synonyms, score_run

app = FastAPI(title="mr-context-llm-eval")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "scenes")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


class EvaluateRequest(BaseModel):
    scene: Scene
    mode: str = "context"
    backend: str = "mock"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mr-context-llm-eval"}


@app.get("/scenes")
def list_scenes() -> dict:
    scenes = load_scenes(DATA_DIR)
    return {
        "scenes": [
            {"scene_id": s.scene_id, "domain": s.domain, "query": s.user_query}
            for s in scenes
        ]
    }


@app.get("/scenes/{scene_id}")
def get_scene(scene_id: str) -> dict:
    scenes = load_scenes(DATA_DIR)
    for s in scenes:
        if s.scene_id == scene_id:
            return s.model_dump()
    raise HTTPException(status_code=404, detail="scene not found")


@app.post("/evaluate")
def evaluate(req: EvaluateRequest) -> dict:
    if req.mode not in ("blind", "context"):
        raise HTTPException(status_code=400, detail="mode must be blind or context")
    if req.backend not in ("mock", "live"):
        raise HTTPException(status_code=400, detail="backend must be mock or live")
    try:
        out = generate(req.scene, req.mode, req.backend)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    synonyms = load_synonyms(os.path.join(DATA_DIR, "synonyms.json"))
    scores, checks = score_run(
        out.answer, out.spatial_claims, out.ui_schema, req.scene, out.schema_valid, synonyms
    )
    return {
        "scene_id": req.scene.scene_id,
        "mode": req.mode,
        "backend": out.backend,
        "model": out.model,
        "answer": out.answer,
        "spatial_claims": out.spatial_claims,
        "spatial_checks": [c.model_dump() for c in checks],
        "ui_schema": [i.model_dump() for i in out.ui_schema],
        "gate_decisions": [g.model_dump() for g in out.gate_decisions],
        "scores": scores.model_dump(),
        "schema_valid": out.schema_valid,
        "schema_errors": out.schema_errors,
    }


if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
