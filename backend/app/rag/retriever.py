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


def _text_overlap(t1: str, t2: str) -> float:
    """Compute token Jaccard similarity between two chunk texts to detect near-duplicates."""
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)


def _filter_and_prune(
    chunks: list[ScoredChunk],
    limit: int,
    dropoff_threshold: float,
    token_budget: int,
) -> list[ScoredChunk]:
    if not chunks:
        return []
    best_score = chunks[0].score
    min_allowed_score = best_score - dropoff_threshold

    per_source: dict[str, int] = {}
    kept: list[ScoredChunk] = []
    used_tokens = 0

    for chunk in chunks:
        # 1. Score dropoff: skip chunks whose relevance drops significantly below the best match
        if chunk.score < min_allowed_score:
            continue

        # 2. Source diversification limit
        sid = chunk.payload.source_id
        if per_source.get(sid, 0) >= MAX_CHUNKS_PER_SOURCE:
            continue

        # 3. Text deduplication: skip redundant / near-duplicate chunks
        text = chunk.payload.text
        if any(_text_overlap(text, existing.payload.text) > 0.60 for existing in kept):
            continue

        # 4. Context token budget: approximate 1 token ~= 4 characters
        chunk_tokens = max(1, len(text) // 4)
        if kept and (used_tokens + chunk_tokens > token_budget):
            break

        per_source[sid] = per_source.get(sid, 0) + 1
        kept.append(chunk)
        used_tokens += chunk_tokens

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
    max_chunks = top_k or settings.max_chunks_to_llm
    min_score = settings.gate_for_language(language) if min_score is None else min_score

    vector = get_embedder().embed_query(question)
    # Fetch ample candidates from vector store to prune and deduplicate
    fetch_k = max(settings.retrieval_top_k * 3, max_chunks * 3)
    raw = get_vector_store().search(vector, top_k=fetch_k)
    raw.sort(key=lambda c: c.score, reverse=True)
    best = raw[0].score if raw else None

    # Filter by minimum relevance gate
    above_gate = [c for c in raw if c.score >= min_score]
    strong = _filter_and_prune(
        above_gate,
        limit=max_chunks,
        dropoff_threshold=settings.score_dropoff_threshold,
        token_budget=settings.context_token_budget,
    )
    # If no evidence cleared the gate, surface up to 2 weak matches for fallback info
    weak = [c for c in raw if c.score < min_score][:2] if not strong else []

    log.info(
        "retrieved %d candidates, %d above gate %.2f, %d selected for LLM (best=%s)",
        len(raw),
        len(above_gate),
        min_score,
        len(strong),
        f"{best:.3f}" if best else "n/a",
    )
    return RetrievalResult(chunks=strong, weak=weak, best_score=best, min_score=min_score)
