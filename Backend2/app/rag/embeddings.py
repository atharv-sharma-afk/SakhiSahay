"""
Embedding module — wraps sentence-transformers for text encoding.
Singleton pattern: model is loaded once and reused.
"""
from __future__ import annotations

import logging
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded. Dimension: %d", settings.embedding_dim)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Encode a list of strings into embedding vectors.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of float vectors (one per input string).
    """
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [v.tolist() for v in vectors]


def embed_query(query: str) -> List[float]:
    """Embed a single query string."""
    results = embed_texts([query])
    return results[0] if results else []
