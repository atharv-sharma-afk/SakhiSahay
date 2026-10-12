"""
Qdrant vector store wrapper.
Supports both local persistent mode and server mode.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[Any] = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    from qdrant_client import QdrantClient

    if settings.use_local_qdrant:
        logger.info("Using Qdrant LOCAL mode at: %s", settings.qdrant_local_path)
        _client = QdrantClient(path=settings.qdrant_local_path)
    else:
        logger.info("Connecting to Qdrant server: %s", settings.qdrant_url)
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client


# ── Collection management ─────────────────────────────────────────────────────

def ensure_collection() -> None:
    """Create the Qdrant collection if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams

    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        logger.info("Creating collection '%s'", settings.qdrant_collection)
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Collection created.")
    else:
        logger.debug("Collection '%s' already exists.", settings.qdrant_collection)


def collection_info() -> Dict[str, Any]:
    """Return info about the collection (point count etc.)."""
    client = _get_client()
    try:
        info = client.get_collection(settings.qdrant_collection)
        return {
            "exists": True,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": str(info.status),
        }
    except Exception:
        return {"exists": False, "points_count": 0}


# ── Upsert ────────────────────────────────────────────────────────────────────

def upsert_chunks(chunks, vectors: List[List[float]]) -> int:
    """
    Upsert chunks into the Qdrant collection.

    Args:
        chunks:  List of Chunk objects.
        vectors: Parallel list of embedding vectors.

    Returns:
        Number of points upserted.
    """
    from qdrant_client.models import PointStruct

    client = _get_client()
    points = []
    for chunk, vector in zip(chunks, vectors):
        payload = {
            "text": chunk.text,
            "filename": chunk.filename,
            "title": chunk.title,
            "category": chunk.category,
            "source_org": chunk.source_org,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "checksum": chunk.checksum,
        }
        if chunk.page_start is not None:
            payload["page_start"] = chunk.page_start
        if chunk.page_end is not None:
            payload["page_end"] = chunk.page_end

        # Use first 16 hex chars of chunk_id as integer-compatible UUID-like ID
        # Qdrant requires integer or UUID point IDs
        import uuid
        point_id = str(uuid.UUID(chunk.chunk_id[:8].ljust(32, "0")))

        points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    if not points:
        return 0

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


# ── Delete by filename ────────────────────────────────────────────────────────

def delete_by_filename(filename: str) -> int:
    """
    Remove all chunks associated with a specific filename.

    Returns:
        Estimated number of deleted points.
    """
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = _get_client()
    result = client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="filename",
                    match=MatchValue(value=filename),
                )
            ]
        ),
    )
    logger.info("Deleted chunks for '%s': %s", filename, result)
    return 0  # Qdrant delete result doesn't reliably return count


# ── Semantic search ───────────────────────────────────────────────────────────

def search(
    query_vector: List[float],
    top_k: int = None,
    score_threshold: float = None,
) -> List[Dict[str, Any]]:
    """
    Search the collection for the most relevant chunks.

    Args:
        query_vector:    Embedding of the user query.
        top_k:           Maximum number of results.
        score_threshold: Minimum score to include a result.

    Returns:
        List of dicts with 'text', 'score', and source metadata.
    """
    if top_k is None:
        top_k = settings.retrieval_top_k
    if score_threshold is None:
        score_threshold = settings.retrieval_score_threshold

    client = _get_client()

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        with_payload=True,
    )

    hits = []
    for r in results:
        payload = r.payload or {}
        hits.append(
            {
                "text": payload.get("text", ""),
                "score": round(r.score, 4),
                "filename": payload.get("filename", ""),
                "title": payload.get("title", "Unknown"),
                "category": payload.get("category", ""),
                "source_org": payload.get("source_org", ""),
                "page_start": payload.get("page_start"),
                "chunk_index": payload.get("chunk_index", 0),
            }
        )
    return hits
