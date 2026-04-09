from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PersistentMemory:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._chroma = None
        self._fallback_path = self.data_dir / "memory_fallback.jsonl"
        self._setup_backend()

    def _setup_backend(self) -> None:
        try:
            import chromadb

            self._chroma = chromadb.PersistentClient(path=str(self.data_dir / "chroma"))
        except Exception:
            self._chroma = None

    def commit(self, collection: str, item_id: str, text: str, metadata: dict[str, Any]) -> None:
        if self._chroma:
            col = self._chroma.get_or_create_collection(collection)
            col.add(documents=[text], ids=[item_id], metadatas=[metadata])
            return

        with self._fallback_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "collection": collection,
                        "id": item_id,
                        "text": text,
                        "metadata": metadata,
                    }
                )
                + "\n"
            )

    def query(self, collection: str, query_text: str, limit: int = 3) -> list[dict[str, Any]]:
        if self._chroma:
            col = self._chroma.get_or_create_collection(collection)
            result = col.query(query_texts=[query_text], n_results=limit)
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            ids = result.get("ids", [[]])[0]
            return [
                {"id": ids[i], "text": docs[i], "metadata": metas[i]}
                for i in range(len(docs))
            ]

        if not self._fallback_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        with self._fallback_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("collection") == collection and query_text.lower() in rec.get(
                    "text", ""
                ).lower():
                    rows.append(
                        {
                            "id": rec.get("id"),
                            "text": rec.get("text"),
                            "metadata": rec.get("metadata", {}),
                        }
                    )
        return rows[:limit]
