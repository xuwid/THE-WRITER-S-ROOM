from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
        self.project_root = project_root
        self.output_dir = project_root / "outputs"
        self.image_dir = self.output_dir / "image_assets"
        self.data_dir = project_root / "data"
        self.scene_manifest_path = self.output_dir / "scene_manifest.json"
        self.character_db_path = self.output_dir / "character_db.json"
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.huggingface_token = os.getenv(
            "HUGGINGFACE_TOKEN", os.getenv("huggingface_token", "")
        )
        self.huggingface_model = os.getenv(
            "HUGGINGFACE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0"
        )


settings = Settings()
