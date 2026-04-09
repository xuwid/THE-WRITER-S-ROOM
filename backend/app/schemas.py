from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    mode: Literal["manual", "autonomous"] = Field(
        ..., description="Input mode for script intake"
    )
    prompt: str | None = Field(default=None, description="Prompt for autonomous mode")
    manual_script: str | None = Field(
        default=None, description="Manual script text for manual mode"
    )
    approved: bool = Field(
        default=False,
        description="Human-in-the-loop approval for continuing past checkpoint",
    )
    session_id: str | None = Field(default=None)


class ApproveRequest(BaseModel):
    session_id: str
    approved: bool = True


class ApiResponse(BaseModel):
    status: str
    session_id: str | None = None
    needs_approval: bool = False
    scene_manifest: dict[str, Any] | None = None
    character_db: list[dict[str, Any]] | None = None
    image_assets: list[str] = Field(default_factory=list)
    message: str | None = None


class ToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
