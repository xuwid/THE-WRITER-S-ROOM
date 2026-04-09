from __future__ import annotations

import json
import re
from typing import Any

import requests


def _extract_json_block(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()
    if raw_text.startswith("{"):
        return json.loads(raw_text)

    match = re.search(r"\{[\s\S]*\}", raw_text)
    if not match:
        raise ValueError("LLM output did not contain a valid JSON object")
    return json.loads(match.group(0))


def generate_script_segment(
    prompt: str,
    groq_api_key: str,
    model: str = "llama-3.3-70b-versatile",
    max_scenes: int = 3,
) -> dict[str, Any]:
    if not groq_api_key:
        scenes = []
        for i in range(1, max_scenes + 1):
            scenes.append(
                {
                    "scene_id": i,
                    "heading": f"SCENE {i}",
                    "beats": [
                        {
                            "type": "action",
                            "text": f"The story advances from the prompt: {prompt}",
                        },
                        {
                            "type": "dialogue",
                            "speaker": "NARRATOR",
                            "text": "We move forward with tension and purpose.",
                        },
                    ],
                    "visual_cues": [
                        "cinematic lighting",
                        "medium wide shot",
                        "dynamic composition",
                    ],
                }
            )
        return {
            "title": "Autonomous Draft",
            "logline": prompt,
            "scenes": scenes,
        }

    schema_hint = {
        "title": "Story title",
        "logline": "One-line premise",
        "scenes": [
            {
                "scene_id": 1,
                "heading": "INT./EXT. LOCATION - TIME",
                "beats": [
                    {
                        "type": "action|dialogue",
                        "speaker": "CHARACTER_NAME if dialogue",
                        "text": "beat content",
                    }
                ],
                "visual_cues": ["cue1", "cue2"],
            }
        ],
    }

    payload = {
        "model": model,
        "temperature": 0.8,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Scriptwriter Agent. Convert prompt into a coherent multi-scene screenplay "
                    "JSON with dialogues and visual cues. Return strictly valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Prompt: {prompt}\n"
                    f"Generate up to {max_scenes} scenes. Output schema example: {json.dumps(schema_hint)}"
                ),
            },
        ],
    }

    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    res.raise_for_status()
    content = res.json()["choices"][0]["message"]["content"]
    return _extract_json_block(content)


def validate_and_parse_manual_script(manual_script: str) -> dict[str, Any]:
    lines = [ln.rstrip() for ln in manual_script.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("Manual script is empty")

    scene_header = re.compile(r"^(INT\.|EXT\.|SCENE\s+\d+)", re.IGNORECASE)
    dialogue_line = re.compile(r"^([A-Z][A-Z0-9_ ]{1,30}):\s+(.+)$")

    scenes: list[dict[str, Any]] = []
    current_scene: dict[str, Any] | None = None

    for line in lines:
        if scene_header.match(line):
            if current_scene:
                scenes.append(current_scene)
            current_scene = {
                "scene_id": len(scenes) + 1,
                "heading": line,
                "beats": [],
                "visual_cues": [],
            }
            continue

        if current_scene is None:
            raise ValueError(
                "Script must begin with a scene heading like INT./EXT./SCENE N"
            )

        dm = dialogue_line.match(line)
        if dm:
            current_scene["beats"].append(
                {
                    "type": "dialogue",
                    "speaker": dm.group(1).strip(),
                    "text": dm.group(2).strip(),
                }
            )
        else:
            current_scene["beats"].append({"type": "action", "text": line})

            # Visual cue heuristic from action lines.
            if len(current_scene["visual_cues"]) < 4:
                current_scene["visual_cues"].append(line[:90])

    if current_scene:
        scenes.append(current_scene)

    for sc in scenes:
        if not sc["beats"]:
            raise ValueError(f"Scene '{sc['heading']}' has no action/dialogue lines")

    return {
        "title": "Manual Script",
        "logline": "Imported from user-written screenplay",
        "scenes": scenes,
    }
