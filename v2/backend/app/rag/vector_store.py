"""Qdrant access (embedded local mode by default, server mode when QDRANT_URL is set).

Only general, public knowledge chunks are stored here. Personal tracker
records never enter the vector database.
"""

from __future__ import annotations

import atexit
import logging
import uuid
from dataclasses import asdict, dataclass
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import get_settings

log = logging.getLogger("sakhisahay.vectors")
_NAMESPACE = uuid.UUID("3b4f1a86-6c8c-4a6e-9d0e-5f3e0b1c2d7a")


@dataclass
class ChunkPayload:
    chunk_id: str
    source_id: str
    title: str
    publisher: str
    url: str
    doc_type: str
    topic: str
    section: str | None
    language: str
    published_date: str | None
    updated_date: str | None
    accessed_date: str | None
    license_note: str | None
    text: str


@dataclass
class ScoredChunk:
    score: float
    payload: ChunkPayload


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.collection = settings.qdrant_collection
        if settings.qdrant_url:
            self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
            self.mode = "server"
        else:
            path = settings.resolve_path(settings.qdrant_path)
            path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(path))
            self.mode = "embedded"
        # Close explicitly at exit; the client's __del__ is noisy during interpreter shutdown.
        atexit.register(self._close_quietly)

    def _close_quietly(self) -> None:
        try:
            self.client.close()
        except Exception:  # noqa: BLE001
            pass

    # ---- lifecycle ---------------------------------------------------------
    def ensure_collection(self, dimension: int, recreate: bool = False) -> None:
        exists = self.client.collection_exists(self.collection)
        if exists and recreate:
            self.client.delete_collection(self.collection)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=dimension, distance=qm.Distance.COSINE),
            )
            for field in ("source_id", "topic", "language"):
                self.client.create_payload_index(self.collection, field, qm.PayloadSchemaType.KEYWORD)
            log.info("created collection %s (dim=%d)", self.collection, dimension)

    def is_ready(self) -> bool:
        try:
            return self.client.collection_exists(self.collection) and self.count() > 0
        except Exception:  # pragma: no cover - storage errors surface as "not ready"
            return False

    def count(self) -> int:
        return int(self.client.count(self.collection, exact=True).count)

    # ---- writes ------------------------------------------------------------
    def delete_source(self, source_id: str) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(must=[qm.FieldCondition(key="source_id", match=qm.MatchValue(value=source_id))])
            ),
        )

    def upsert(self, payloads: list[ChunkPayload], vectors: list[list[float]]) -> None:
        points = [
            qm.PointStruct(id=str(uuid.uuid5(_NAMESPACE, p.chunk_id)), vector=v, payload=asdict(p))
            for p, v in zip(payloads, vectors, strict=True)
        ]
        for i in range(0, len(points), 64):
            self.client.upsert(collection_name=self.collection, points=points[i : i + 64], wait=True)

    # ---- reads -------------------------------------------------------------
    def search(self, vector: list[float], top_k: int, topic: str | None = None) -> list[ScoredChunk]:
        query_filter = None
        if topic:
            query_filter = qm.Filter(must=[qm.FieldCondition(key="topic", match=qm.MatchValue(value=topic))])
        result = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            with_payload=True,
            query_filter=query_filter,
        )
        return [ScoredChunk(score=float(p.score), payload=ChunkPayload(**p.payload)) for p in result.points]


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
