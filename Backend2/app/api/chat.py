"""
Chat API router — POST /api/chat, GET /health, GET /api/kb-status
"""
from __future__ import annotations

import logging
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.rag.generation import generate_answer
from app.rag.retrieval import retrieve
from app.rag.prompts import INSUFFICIENT_EVIDENCE_RESPONSE
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    KBStatusResponse,
    SourceDocument,
)
from app.services.safety import check_safety

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Health check ──────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    return HealthResponse(status="ok")


# ── Knowledge-base status ─────────────────────────────────────────────────────

@router.get("/api/kb-status", response_model=KBStatusResponse, tags=["admin"])
async def kb_status():
    try:
        from app.rag.vector_store import collection_info
        info = collection_info()
        from app.rag.vector_store import _get_client
        qdrant_mode = "local" if settings.use_local_qdrant else "server"
        return KBStatusResponse(
            collection=settings.qdrant_collection,
            total_chunks=info.get("points_count") or 0,
            qdrant_mode=qdrant_mode,
            embedding_model=settings.embedding_model,
            gemini_model=settings.gemini_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"KB unavailable: {exc}")


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request_body: ChatRequest, request: Request):
    """
    Main RAG chat endpoint.

    Flow:
      1. Validate & sanitise input.
      2. Run deterministic safety checks.
      3. Retrieve relevant chunks from Qdrant.
      4. Generate grounded answer with Gemini.
      5. Return answer + sources + metadata.
    """
    message = request_body.message.strip()

    # Input length guard
    if len(message) > settings.max_message_length:
        raise HTTPException(
            status_code=422,
            detail=f"Message too long (max {settings.max_message_length} characters).",
        )

    conversation_id = request_body.conversation_id or str(uuid.uuid4())

    # Log question length only (not the question itself) for privacy
    logger.info(
        "Chat request | conv_id=%s | msg_len=%d",
        conversation_id,
        len(message),
    )

    # ── 1. Safety gate ────────────────────────────────────────────────────────
    safety_result = check_safety(message)
    if not safety_result.is_safe:
        logger.info(
            "Safety rule triggered: %s | conv_id=%s",
            safety_result.triggered_rule,
            conversation_id,
        )
        return ChatResponse(
            answer=safety_result.pre_set_response,
            conversation_id=conversation_id,
            sources=[],
            insufficient_evidence=False,
        )

    # ── 2. Retrieve relevant chunks ───────────────────────────────────────────
    try:
        hits = retrieve(message)
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        raise HTTPException(status_code=503, detail="Retrieval service unavailable.")

    insufficient_evidence = len(hits) == 0

    # ── 3. Generate answer ────────────────────────────────────────────────────
    try:
        answer = await generate_answer(message, hits)
    except RuntimeError as exc:
        # Configuration error (missing API key etc.) — surface clearly
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Generation error: %s", exc)
        raise HTTPException(status_code=500, detail="Answer generation failed.")

    # ── 4. Build source list ──────────────────────────────────────────────────
    # Deduplicate by (title, category) — keep highest-scoring hit per source
    seen = {}
    for hit in hits:
        key = (hit.get("title", ""), hit.get("category", ""))
        if key not in seen or hit["score"] > seen[key]["score"]:
            seen[key] = hit

    sources: List[SourceDocument] = []
    for hit in seen.values():
        sources.append(
            SourceDocument(
                title=hit.get("title", "Medical Reference"),
                url=None,          # URL field reserved for future manifest metadata
                category=hit.get("category", ""),
                page=hit.get("page_start"),
                score=hit.get("score"),
            )
        )

    return ChatResponse(
        answer=answer,
        conversation_id=conversation_id,
        sources=sources,
        insufficient_evidence=insufficient_evidence,
    )
