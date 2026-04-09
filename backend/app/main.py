from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.graph_flow import build_workflow
from app.mcp_registry import MCPToolRegistry
from app.memory_store import PersistentMemory
from app.schemas import ApiResponse, ApproveRequest, RunRequest, ToolDescriptor
from app.tools.image_tools import generate_character_image
from app.tools.memory_tools import commit_memory, query_memory, query_stock_footage
from app.tools.script_tools import generate_script_segment, validate_and_parse_manual_script

app = FastAPI(title="PROJECT MONTAGE - Phase 1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.image_dir.mkdir(parents=True, exist_ok=True)
settings.data_dir.mkdir(parents=True, exist_ok=True)

_memory = PersistentMemory(settings.data_dir)
_registry = MCPToolRegistry()

_registry.register(
    name="generate_script_segment",
    description="Generate multi-scene screenplay manifest from prompt",
    input_schema={
        "type": "object",
        "required": ["prompt", "groq_api_key"],
        "properties": {
            "prompt": {"type": "string"},
            "groq_api_key": {"type": "string"},
            "model": {"type": "string"},
            "max_scenes": {"type": "integer"},
        },
    },
    fn=generate_script_segment,
)

_registry.register(
    name="validate_and_parse_manual_script",
    description="Validate uploaded screenplay and convert to standardized JSON",
    input_schema={
        "type": "object",
        "required": ["manual_script"],
        "properties": {"manual_script": {"type": "string"}},
    },
    fn=validate_and_parse_manual_script,
)

_registry.register(
    name="commit_memory",
    description="Persist script/character/image state into vector memory",
    input_schema={
        "type": "object",
        "required": ["collection", "item_id", "text", "metadata"],
        "properties": {
            "collection": {"type": "string"},
            "item_id": {"type": "string"},
            "text": {"type": "string"},
            "metadata": {"type": "object"},
        },
    },
    fn=partial(commit_memory, _memory),
)

_registry.register(
    name="query_memory",
    description="Retrieve related memory items by semantic query",
    input_schema={
        "type": "object",
        "required": ["collection", "query_text"],
        "properties": {
            "collection": {"type": "string"},
            "query_text": {"type": "string"},
            "limit": {"type": "integer"},
        },
    },
    fn=partial(query_memory, _memory),
)

_registry.register(
    name="query_stock_footage",
    description="Discover visual style references for character design",
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {"query": {"type": "string"}},
    },
    fn=query_stock_footage,
)

_registry.register(
    name="generate_character_image",
    description="Generate character image asset from identity metadata",
    input_schema={
        "type": "object",
        "required": ["name", "appearance", "style", "output_dir"],
        "properties": {
            "name": {"type": "string"},
            "appearance": {"type": "string"},
            "style": {"type": "string"},
            "output_dir": {"type": "string"},
            "huggingface_token": {"type": "string"},
            "huggingface_model": {"type": "string"},
        },
    },
    fn=generate_character_image,
)

_graph = build_workflow(_registry)
_checkpoints: dict[str, dict[str, Any]] = {}


def _write_outputs(state: dict[str, Any]) -> None:
    scene_manifest = state.get("scene_manifest") or {}
    character_db = state.get("character_db") or []

    settings.scene_manifest_path.write_text(
        json.dumps(scene_manifest, indent=2), encoding="utf-8"
    )
    settings.character_db_path.write_text(
        json.dumps(character_db, indent=2), encoding="utf-8"
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tools", response_model=list[ToolDescriptor])
def tools() -> list[dict[str, Any]]:
    return _registry.discover_tools()


@app.post("/api/run", response_model=ApiResponse)
def run_pipeline(body: RunRequest) -> ApiResponse:
    if body.mode == "manual" and not body.manual_script:
        raise HTTPException(status_code=400, detail="manual_script is required in manual mode")
    if body.mode == "autonomous" and not body.prompt:
        raise HTTPException(status_code=400, detail="prompt is required in autonomous mode")

    initial_state: dict[str, Any] = {
        "session_id": body.session_id,
        "mode": body.mode,
        "prompt": body.prompt or "",
        "manual_script": body.manual_script or "",
        "approved": body.approved,
    }

    state = _graph.invoke(initial_state)
    if state.get("status") == "error":
        raise HTTPException(status_code=400, detail=state.get("error", "Unknown workflow error"))

    sid = state.get("session_id", "")
    if state.get("needs_approval"):
        _checkpoints[sid] = state
        _write_outputs(state)
        return ApiResponse(
            status="awaiting_approval",
            session_id=sid,
            needs_approval=True,
            scene_manifest=state.get("scene_manifest"),
            message="HITL checkpoint reached. Approve to continue character and image generation.",
        )

    _write_outputs(state)
    return ApiResponse(
        status=state.get("status", "completed"),
        session_id=sid,
        scene_manifest=state.get("scene_manifest"),
        character_db=state.get("character_db", []),
        image_assets=state.get("image_assets", []),
    )


@app.post("/api/approve", response_model=ApiResponse)
def approve_pipeline(body: ApproveRequest) -> ApiResponse:
    if body.session_id not in _checkpoints:
        raise HTTPException(status_code=404, detail="Checkpoint session not found")

    state = _checkpoints.pop(body.session_id)
    state["approved"] = body.approved
    state["needs_approval"] = False

    # Resume through workflow with script already in state.
    resumed_state = _graph.invoke(state)

    if resumed_state.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=resumed_state.get("error", "Unknown workflow error during approval"),
        )

    _write_outputs(resumed_state)
    return ApiResponse(
        status=resumed_state.get("status", "completed"),
        session_id=body.session_id,
        scene_manifest=resumed_state.get("scene_manifest"),
        character_db=resumed_state.get("character_db", []),
        image_assets=resumed_state.get("image_assets", []),
    )


@app.get("/api/outputs")
def outputs() -> dict[str, Any]:
    scene_manifest = {}
    character_db = []

    if settings.scene_manifest_path.exists():
        scene_manifest = json.loads(settings.scene_manifest_path.read_text(encoding="utf-8"))
    if settings.character_db_path.exists():
        character_db = json.loads(settings.character_db_path.read_text(encoding="utf-8"))

    images = [str(p) for p in sorted(settings.image_dir.glob("*.png"))]
    return {
        "scene_manifest": scene_manifest,
        "character_db": character_db,
        "image_assets": images,
    }


@app.get("/api/images/{name}")
def get_image(name: str):
    path = settings.image_dir / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


project_root = Path(__file__).resolve().parents[2]
frontend_dir = project_root / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
