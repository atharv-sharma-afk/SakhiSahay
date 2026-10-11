from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.rag.pipeline import KnowledgeIndexUnavailable, answer_question
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import tracker_service
from app.services.insights_service import compute_stats

router = APIRouter(prefix="/api/chat", tags=["assistant"])
log = logging.getLogger("sakhisahay.chat")


def _tracker_context(db: DbSession, user_id: str) -> str | None:
    """Numeric-only summary of the user's own records. Free-text notes are never included."""
    periods = tracker_service.list_periods(db, user_id)
    if not periods:
        return None
    stats = compute_stats(periods)
    lines = [f"- Logged periods: {stats.logged_periods}"]
    if stats.cycle_lengths_days:
        lines.append(
            f"- Recorded cycle lengths (days between period starts): {', '.join(map(str, stats.cycle_lengths_days))}"
        )
    if stats.average_period_duration is not None:
        lines.append(f"- Average recorded period duration: {stats.average_period_duration:g} days")
    if stats.days_since_last_period_start is not None:
        lines.append(f"- Days since last recorded period start: {stats.days_since_last_period_start}")
    symptoms = tracker_service.list_symptoms(db, user_id)
    if symptoms:
        counts: dict[str, int] = {}
        for s in symptoms:
            counts[s.symptom] = counts.get(s.symptom, 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
        lines.append("- Most logged symptoms: " + ", ".join(f"{k} ({v} entries)" for k, v in top))
    return "\n".join(lines)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession, user: CurrentUser) -> ChatResponse:
    """Answer a women's-health question with retrieved, cited evidence.

    Synchronous on purpose: embedding and generation are blocking calls and
    FastAPI runs sync handlers in a worker thread pool.
    """
    context = _tracker_context(db, user.id) if payload.include_tracker_context else None
    try:
        response = answer_question(payload.question, payload.language, tracker_context=context)
    except KnowledgeIndexUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except Exception:  # noqa: BLE001
        # Never leak internals (or the question) into logs or the response.
        log.exception("chat pipeline failure")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "The assistant hit an unexpected error. Please try again.")
    # Only counts and timings are logged; never the question or answer text.
    log.info("chat ok mode=%s lang=%s sources=%d ms=%d", response.mode, response.language_used, len(response.sources), response.latency_ms)
    return response
