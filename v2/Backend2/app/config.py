"""
SakhiSahay Backend — Application Configuration
Loads settings from environment variables / .env file.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent  # Backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    google_api_key: str = Field("", description="Google Gemini API key")
    gemini_model: str = Field("gemini-1.5-flash", description="Gemini model name")

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace sentence-transformers model ID",
    )
    embedding_dim: int = Field(384, description="Embedding vector dimension")

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str = Field("", description="Qdrant server URL (empty = local mode)")
    qdrant_api_key: str = Field("", description="Qdrant Cloud API key")
    qdrant_local_path: str = Field(
        str(BASE_DIR / "qdrant_storage"),
        description="Local persistent storage directory for Qdrant",
    )
    qdrant_collection: str = Field(
        "sakhisahay_knowledge", description="Qdrant collection name"
    )

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieval_top_k: int = Field(5, ge=1, le=20)
    retrieval_score_threshold: float = Field(0.35, ge=0.0, le=1.0)

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_size_tokens: int = Field(800, ge=100, le=4000)
    chunk_overlap_tokens: int = Field(120, ge=0, le=500)

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000)
    cors_origins: str = Field("http://localhost:3000,http://127.0.0.1:3000")
    max_message_length: int = Field(2000, ge=10, le=10000)

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field("INFO")

    # ── Data paths ────────────────────────────────────────────────────────────
    data_raw_dir: Path = Field(default_factory=lambda: BASE_DIR / "data" / "raw")
    manifest_path: Path = Field(
        default_factory=lambda: BASE_DIR / "data" / "manifest" / "index.json"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def coerce_cors(cls, v: object) -> str:
        return str(v)

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_local_qdrant(self) -> bool:
        return not bool(self.qdrant_url.strip())


# Singleton — import this everywhere
settings = Settings()
