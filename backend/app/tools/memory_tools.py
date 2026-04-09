from __future__ import annotations

from typing import Any

from app.memory_store import PersistentMemory


def commit_memory(
    memory: PersistentMemory,
    collection: str,
    item_id: str,
    text: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    memory.commit(collection=collection, item_id=item_id, text=text, metadata=metadata)
    return {"ok": True, "collection": collection, "id": item_id}


def query_memory(
    memory: PersistentMemory,
    collection: str,
    query_text: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    return memory.query(collection=collection, query_text=query_text, limit=limit)


def query_stock_footage(query: str) -> list[dict[str, str]]:
    # Placeholder catalogue; this is exposed as an MCP-discoverable tool.
    references = [
        {"style": "neo-noir", "description": "high-contrast urban cinematic look"},
        {"style": "realist drama", "description": "natural light, grounded palette"},
        {"style": "retro-futurist", "description": "saturated highlights, stylized wardrobe"},
    ]
    q = query.lower()
    return [r for r in references if any(tok in r["style"] for tok in q.split())] or references[:2]
