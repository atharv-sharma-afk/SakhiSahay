"""
Retrieval pipeline — embeds the user query and fetches relevant chunks.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List

from app.config import settings
from app.rag.embeddings import embed_query
from app.rag.vector_store import search

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    top_k: int = None,
    score_threshold: float = None,
) -> List[Dict[str, Any]]:
    """
    Embed the query and retrieve the top-k most relevant chunks.

    Args:
        query:           User's natural-language question.
        top_k:           Override default retrieval_top_k.
        score_threshold: Override default retrieval_score_threshold.

    Returns:
        List of chunk dicts sorted by descending relevance score.
    """
    # Normalise whitespace
    query = " ".join(query.split())

    if not query:
        return []

    if top_k is None:
        top_k = settings.retrieval_top_k
    if score_threshold is None:
        score_threshold = settings.retrieval_score_threshold

    logger.debug("Embedding query: %r", query[:80])
    query_vector = embed_query(query)

    if not query_vector:
        logger.error("Failed to generate query embedding.")
        return []

    hits = search(query_vector, top_k=top_k, score_threshold=score_threshold)
    logger.debug("Retrieved %d chunks (threshold=%.2f)", len(hits), score_threshold)
    return hits
