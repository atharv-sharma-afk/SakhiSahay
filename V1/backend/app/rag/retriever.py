from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import get_settings
from app.rag.embeddings import get_embedder
from app.rag.vector_store import ScoredChunk, get_vector_store

log = logging.getLogger("sakhisahay.retriever")

MAX_CHUNKS_PER_SOURCE = 2


@dataclass
class RetrievalResult:
    chunks: list[ScoredChunk]  # passed the relevance gate, diversified by source
    weak: list[ScoredChunk]  # below the gate; shown only as "possibly related"
    best_score: float | None
    min_score: float


def _diversify(chunks: list[ScoredChunk], limit: int) -> list[ScoredChunk]:
    per_source: dict[str, int] = {}
    kept: list[ScoredChunk] = []
    for chunk in chunks:
        sid = chunk.payload.source_id
        if per_source.get(sid, 0) >= MAX_CHUNKS_PER_SOURCE:
            continue
        per_source[sid] = per_source.get(sid, 0) + 1
        kept.append(chunk)
        if len(kept) >= limit:
            break
    return kept


def evidence_strength(best_score: float | None, min_score: float) -> str:
    """Coarse, explainable label shown to users: how far above the gate the best match sits."""
    if best_score is None or best_score < min_score:
        return "none"
    if best_score >= min_score + 0.06:
        return "strong"
    if best_score >= min_score + 0.02:
        return "moderate"
    return "weak"


def retrieve(
    question: str,
    top_k: int | None = None,
    min_score: float | None = None,
    language: str = "en",
) -> RetrievalResult:
    settings = get_settings()
    top_k = top_k or settings.retrieval_top_k
    min_score = settings.gate_for_language(language) if min_score is None else min_score

    vector = get_embedder().embed_query(question)
    # Over-fetch so that per-source diversification still fills top_k.
    raw = get_vector_store().search(vector, top_k=top_k * 3)
    raw.sort(key=lambda c: c.score, reverse=True)
    best = raw[0].score if raw else None

    strong = _diversify([c for c in raw if c.score >= min_score], top_k)
    weak = _diversify([c for c in raw if c.score < min_score], 2) if not strong else []
    log.info("retrieved %d candidates, %d above gate %.2f (best=%s)", len(raw), len(strong), min_score, f"{best:.3f}" if best else "n/a")
    return RetrievalResult(chunks=strong, weak=weak, best_score=best, min_score=min_score)
