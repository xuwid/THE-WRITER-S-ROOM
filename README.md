# THE WRITER'S ROOM
## PROJECT MONTAGE PHASE 1: INTENT -> SCENES -> CHARACTERS -> IMAGES

Welcome to a controlled creative explosion.

This project is a multi-agent screenplay machine where human intent is ingested,
expanded, validated, and transformed into production-shaped artifacts:

- scene_manifest.json
- character_db.json
- image_assets/*.png

No duct-taped spaghetti prompts. No random tool calls.
This is stateful orchestration with agent roles, memory, MCP-style tool discovery,
and a real human-in-the-loop checkpoint.

## Why This Exists

Agentic AI Phase 1 asks for a system that turns vague human ideas into a structured narrative layer.
This repo does exactly that through a Supervisor-Worker pattern in LangGraph.

## Agent Cast

- Scriptwriter Agent
- Script Validator Agent
- Human-in-the-Loop Agent
- Character Designer Agent
- Image Synthesizer Agent
- Memory Commit Layer

## Workflow Graph (LangGraph)

- mode_selector
- validator
- scriptwriter
- hitl
- character
- image
- memory

Routing behavior:

- Manual mode -> validator -> hitl
- Autonomous mode -> scriptwriter -> hitl
- Approved -> character -> image -> memory

## MCP-Style Dynamic Tooling

Discovered at runtime via registry:

- generate_script_segment
- validate_and_parse_manual_script
- commit_memory
- query_memory
- query_stock_footage
- generate_character_image

## Memory Layer

- Preferred: ChromaDB (if installed)
- Guaranteed fallback: JSONL persistence in data/memory_fallback.jsonl

This gives continuity and resilient recovery even on constrained environments.

## Image Generation

The image synthesizer attempts Hugging Face inference first.
If unavailable, it auto-falls back to deterministic local rendering.

Each generated image includes a sidecar marker:

- *.source.txt = huggingface
- *.source.txt = fallback

So you can prove which path was used.

## Run It

```bash
cd "/Users/Apple/Documents/Semester 8/Agentic AI/Ass3"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open:

- http://127.0.0.1:8000

## Minimal API Surface

- GET /api/health
- GET /api/tools
- POST /api/run
- POST /api/approve
- GET /api/outputs
- GET /api/images/{name}

## Copy-Paste Verification

```bash
cd "/Users/Apple/Documents/Semester 8/Agentic AI/Ass3"

resp=$(curl -s -X POST http://127.0.0.1:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "mode":"manual",
    "manual_script":"INT. LAB - NIGHT\nAALIYA: We only have one try.\nBILAL: Then we make it count.\nA sensor blinks red.",
    "approved":false
  }')

echo "$resp" | jq '{status, needs_approval, session_id}'
sid=$(echo "$resp" | jq -r '.session_id')

curl -s -X POST http://127.0.0.1:8000/api/approve \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$sid\",\"approved\":true}" \
| jq '{status, characters:(.character_db|length), images:(.image_assets|length)}'

curl -s http://127.0.0.1:8000/api/outputs \
| jq '{scene_count:(.scene_manifest.scenes|length), character_count:(.character_db|length), image_count:(.image_assets|length)}'
```

## Assignment Deliverables Map

- Structured screenplay: outputs/scene_manifest.json
- Character identity store: outputs/character_db.json
- Character visuals: outputs/image_assets/
- LangGraph workflow: backend/app/graph_flow.py
- MCP integration: backend/app/mcp_registry.py + main registrations

## Final Note

This repo is designed for demos under pressure:
if cloud image generation fails, outputs still complete;
if vector DB is unavailable, memory still persists;
if manual script is malformed, validator fails early with clear errors.

Exactly what you want before submission.
