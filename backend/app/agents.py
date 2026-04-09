from __future__ import annotations

import json
import re
import uuid
from typing import Any, TypedDict

from app.config import settings
from app.mcp_registry import MCPToolRegistry


class WorkflowState(TypedDict, total=False):
    session_id: str
    mode: str
    prompt: str
    manual_script: str
    approved: bool
    needs_approval: bool
    status: str
    error: str
    scene_manifest: dict[str, Any]
    character_db: list[dict[str, Any]]
    image_assets: list[str]


def mode_selector_node(state: WorkflowState) -> WorkflowState:
    if not state.get("session_id"):
        state["session_id"] = str(uuid.uuid4())

    state["status"] = "mode_selected"
    return state


def script_validator_node(state: WorkflowState, registry: MCPToolRegistry) -> WorkflowState:
    try:
        parsed = registry.invoke(
            "validate_and_parse_manual_script",
            {"manual_script": state.get("manual_script", "")},
        )
        state["scene_manifest"] = parsed
        state["status"] = "manual_script_validated"
    except Exception as ex:
        state["status"] = "error"
        state["error"] = f"Manual script validation failed: {ex}"
    return state


def scriptwriter_node(state: WorkflowState, registry: MCPToolRegistry) -> WorkflowState:
    try:
        generated = registry.invoke(
            "generate_script_segment",
            {
                "prompt": state.get("prompt", ""),
                "groq_api_key": settings.groq_api_key,
                "model": settings.groq_model,
                "max_scenes": 4,
            },
        )
        state["scene_manifest"] = generated
        state["status"] = "autonomous_script_generated"
    except Exception as ex:
        state["status"] = "error"
        state["error"] = f"Script generation failed: {ex}"
    return state


def hitl_node(state: WorkflowState) -> WorkflowState:
    if state.get("approved"):
        state["needs_approval"] = False
        state["status"] = "approved"
    else:
        state["needs_approval"] = True
        state["status"] = "awaiting_approval"
    return state


def _infer_character_style(name: str) -> str:
    styles = ["neo-noir portrait", "editorial realism", "cinematic drama"]
    return styles[len(name) % len(styles)]


def character_designer_node(state: WorkflowState, registry: MCPToolRegistry) -> WorkflowState:
    manifest = state.get("scene_manifest", {})
    scenes = manifest.get("scenes", []) if isinstance(manifest, dict) else []

    names: set[str] = set()
    for scene in scenes:
        for beat in scene.get("beats", []):
            speaker = beat.get("speaker")
            if beat.get("type") == "dialogue" and speaker:
                names.add(str(speaker).strip())

            # Handle lines such as "ALEX enters..." in action beats.
            if beat.get("type") == "action":
                for token in re.findall(r"\b[A-Z][A-Z]{2,}\b", beat.get("text", "")):
                    if token not in {"INT", "EXT", "SCENE"}:
                        names.add(token)

    if not names:
        names = {"PROTAGONIST"}

    character_db: list[dict[str, Any]] = []
    for idx, name in enumerate(sorted(names), start=1):
        refs = registry.invoke("query_stock_footage", {"query": _infer_character_style(name)})
        character_db.append(
            {
                "id": f"char_{idx:03d}",
                "name": name,
                "personality_traits": ["driven", "observant", "emotionally layered"],
                "appearance": f"{name.title()} with distinct silhouette, expressive eyes, and scene-aware wardrobe.",
                "reference_style": refs[0]["style"] if refs else "cinematic",
            }
        )

    state["character_db"] = character_db
    state["status"] = "characters_designed"
    return state


def image_synthesis_node(state: WorkflowState, registry: MCPToolRegistry) -> WorkflowState:
    assets: list[str] = []
    for character in state.get("character_db", []):
        asset = registry.invoke(
            "generate_character_image",
            {
                "name": character["name"],
                "appearance": character["appearance"],
                "style": character["reference_style"],
                "output_dir": str(settings.image_dir),
                "huggingface_token": settings.huggingface_token,
                "huggingface_model": settings.huggingface_model,
            },
        )
        assets.append(asset)

    state["image_assets"] = assets
    state["status"] = "images_generated"
    return state


def memory_commit_node(state: WorkflowState, registry: MCPToolRegistry) -> WorkflowState:
    sid = state.get("session_id", str(uuid.uuid4()))

    registry.invoke(
        "commit_memory",
        {
            "collection": "scripts",
            "item_id": f"{sid}_script",
            "text": json.dumps(state.get("scene_manifest", {})),
            "metadata": {"session_id": sid, "type": "scene_manifest"},
        },
    )

    registry.invoke(
        "commit_memory",
        {
            "collection": "characters",
            "item_id": f"{sid}_characters",
            "text": json.dumps(state.get("character_db", [])),
            "metadata": {"session_id": sid, "type": "character_db"},
        },
    )

    state["status"] = "memory_committed"
    return state
