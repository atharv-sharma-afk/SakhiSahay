from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import AppSettings, DbSession
from app.db import models

router = APIRouter(tags=["system"])


@router.get("/api/health")
def health(settings: AppSettings, db: DbSession) -> dict:
    """Liveness plus a non-sensitive capability summary used by the UI status bar."""
    from app.rag.pipeline import get_pipeline_status  # local import keeps startup light

    source_count = db.scalar(
        select(func.count()).select_from(models.KnowledgeSource).where(models.KnowledgeSource.status == "indexed")
    )
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "auth_mode": settings.auth_mode,
        "llm": {
            "provider": settings.llm_provider if settings.llm_enabled else "none",
            "model": settings.gemini_model if settings.llm_enabled else None,
            "configured": settings.llm_enabled,
        },
        "knowledge": {
            "indexed_sources": int(source_count or 0),
            "embedding_model": settings.embedding_model,
            **get_pipeline_status(),
        },
    }
