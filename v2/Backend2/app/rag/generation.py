"""
LLM generation module — uses Google Gemini to produce RAG answers.
"""
from __future__ import annotations

import logging
import textwrap
from typing import Any, Dict, List

from app.config import settings
from app.rag.prompts import INSUFFICIENT_EVIDENCE_RESPONSE, SAKHI_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_gemini_model = None


def _get_gemini():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. "
            "Set it in Backend/.env before starting the server."
        )

    import google.generativeai as genai

    genai.configure(api_key=settings.google_api_key)
    _gemini_model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=SAKHI_SYSTEM_PROMPT,
    )
    logger.info("Gemini model ready: %s", settings.gemini_model)
    return _gemini_model


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(hits: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a numbered context block for the LLM."""
    parts = []
    for i, hit in enumerate(hits, 1):
        title = hit.get("title", "Unknown document")
        org = hit.get("source_org", "")
        score = hit.get("score", 0)
        text = hit.get("text", "")
        header = f"[{i}] Source: {title} ({org}) | Relevance: {score:.2f}"
        parts.append(f"{header}\n{text}")
    return "\n\n─────\n\n".join(parts)


# ── Main generation function ──────────────────────────────────────────────────

async def generate_answer(
    user_question: str,
    hits: List[Dict[str, Any]],
) -> str:
    """
    Generate a grounded answer using Gemini and retrieved context.

    Args:
        user_question: The user's health question.
        hits:          Retrieved chunks from Qdrant.

    Returns:
        Natural-language answer string.
    """
    if not hits:
        return INSUFFICIENT_EVIDENCE_RESPONSE

    context = _build_context(hits)

    prompt = textwrap.dedent(f"""
        RETRIEVED MEDICAL KNOWLEDGE (use as primary factual source):
        ──────────────────────────────────────────────────────────
        {context}
        ──────────────────────────────────────────────────────────

        USER QUESTION:
        {user_question}

        Please answer the user's question using the retrieved information above.
        If the context does not adequately address the question, say so honestly
        rather than guessing.
    """).strip()

    try:
        model = _get_gemini()
        response = await model.generate_content_async(prompt)
        answer = response.text.strip()
        if not answer:
            return INSUFFICIENT_EVIDENCE_RESPONSE
        return answer
    except Exception as exc:
        logger.error("Gemini generation error: %s", exc)
        raise RuntimeError(f"LLM generation failed: {exc}") from exc
