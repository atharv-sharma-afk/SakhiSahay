from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DbSession
from app.db import models

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    publisher: str
    url: str
    doc_type: str
    topic: str
    language: str
    published_date: str | None
    updated_date: str | None
    accessed_date: str | None
    license_note: str | None
    chunk_count: int
    status: str


@router.get("/sources", response_model=list[KnowledgeSourceOut])
def list_sources(db: DbSession):
    """Every source the assistant can cite, with ingestion status (transparency view)."""
    stmt = select(models.KnowledgeSource).order_by(models.KnowledgeSource.publisher, models.KnowledgeSource.title)
    return list(db.scalars(stmt))
