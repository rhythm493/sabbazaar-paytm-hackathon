from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"

    model_enabled: bool = True
    model_provider: str = "google_genai"
    model_name: str = ""
    model_api_key: str = ""
    model_base_url: str = ""

    # "shopify" uses the real Shopify operations adapter (blocked honestly if not connected);
    # "fake" registers a clearly labelled simulated channel for local demos and tests.
    channel_mode: Literal["shopify", "fake"] = "shopify"

    upload_dir: Path = REPO_ROOT / "data" / "uploads"
    checkpoint_path: Path = REPO_ROOT / "data" / "checkpoints.sqlite"
    fixture_dir: Path = REPO_ROOT / "tests" / "fixtures" / "bills"
    max_upload_bytes: int = 10 * 1024 * 1024
