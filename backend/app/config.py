from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment variables or backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    auth_mode: Literal["local", "jwt"] = "local"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./data/runtime/sakhisahay.db"

    llm_provider: Literal["gemini", "none"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = 40.0

    embedding_model: str = "intfloat/multilingual-e5-small"
    qdrant_path: str = "./data/runtime/qdrant"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "sakhisahay_knowledge"

    retrieval_top_k: int = Field(default=6, ge=1, le=20)
    max_chunks_to_llm: int = Field(default=4, ge=1, le=10)
    context_token_budget: int = Field(default=1000, ge=200, le=4000)
    score_dropoff_threshold: float = Field(default=0.06, ge=0.01, le=0.20)

    # Cosine-similarity gates below which evidence is treated as insufficient.
    # multilingual-e5 compresses scores into ~0.75-0.93. Calibrated on
    # evaluation/eval_questions.yaml: unrelated queries score ~0.80-0.81, while
    # valid health topics score >= 0.85 (en), >= 0.78 (hi), >= 0.80 (hinglish).
    retrieval_min_score: float = Field(default=0.82, ge=0.0, le=1.0)
    retrieval_min_score_hi: float = Field(default=0.78, ge=0.0, le=1.0)
    retrieval_min_score_hinglish: float = Field(default=0.80, ge=0.0, le=1.0)

    gemini_max_output_tokens: int = Field(default=800, ge=100, le=2000)
    gemini_temperature: float = Field(default=0.1, ge=0.0, le=1.0)

    def gate_for_language(self, language: str) -> float:
        if language == "hi":
            return self.retrieval_min_score_hi
        if language == "hinglish":
            return self.retrieval_min_score_hinglish
        return self.retrieval_min_score

    knowledge_dir: Path = BACKEND_DIR / "data" / "knowledge"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    @property
    def resolved_database_url(self) -> str:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix) and not self.database_url.startswith(prefix + "/"):
            relative = self.database_url[len(prefix) :]
            if relative.startswith("./"):
                relative = relative[2:]
            return prefix + str((BACKEND_DIR / relative).resolve())
        return self.database_url

    @property
    def llm_enabled(self) -> bool:
        return (
            self.llm_provider == "gemini"
            and bool(self.gemini_api_key)
            and self.gemini_api_key != "PASTE_YOUR_KEY_HERE"
            and not self.gemini_api_key.startswith("PASTE_")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
