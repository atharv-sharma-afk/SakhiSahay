"""Thin orchestration of the RAG stages. Each stage lives in its own module."""

from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.rag.citations import validate_citations
from app.rag.language import LANGUAGE_LABELS, Language, LanguageChoice, resolve_language
from app.rag.llm.base import LLMUnavailable
from app.rag.llm.factory import get_llm
from app.rag.prompt_builder import build_prompt
from app.rag.retriever import RetrievalResult, evidence_strength, retrieve
from app.rag.safety import EDUCATIONAL_DISCLAIMER, SafetyAssessment, screen_question
from app.rag.vector_store import ScoredChunk, get_vector_store
from app.schemas.chat import ChatResponse, SafetyNoticeOut, SafetyOut, SourceRef

log = logging.getLogger("sakhisahay.pipeline")

EXCERPT_CHARS = 320


class KnowledgeIndexUnavailable(RuntimeError):
    pass


def get_pipeline_status() -> dict:
    try:
        store = get_vector_store()
        ready = store.is_ready()
        return {"index_ready": ready, "chunk_count": store.count() if ready else 0, "vector_store": store.mode}
    except Exception as exc:  # noqa: BLE001
        return {"index_ready": False, "chunk_count": 0, "vector_store": "unavailable", "error": type(exc).__name__}


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= EXCERPT_CHARS else text[: EXCERPT_CHARS - 1].rsplit(" ", 1)[0] + "..."


def _sources(chunks: list[ScoredChunk], cited: list[int], order_cited_first: bool = True) -> list[SourceRef]:
    refs = []
    for i, chunk in enumerate(chunks, start=1):
        p = chunk.payload
        refs.append(
            SourceRef(
                ref=i,
                source_id=p.source_id,
                title=p.title,
                publisher=p.publisher,
                url=p.url,
                doc_type=p.doc_type,
                topic=p.topic,
                section=p.section,
                excerpt=_excerpt(p.text),
                score=round(chunk.score, 3),
                accessed_date=p.accessed_date,
                updated_date=p.updated_date,
                cited=i in cited,
            )
        )
    if order_cited_first and cited:
        refs.sort(key=lambda r: (0, cited.index(r.ref)) if r.ref in cited else (1, r.ref))
    return refs


def _safety_out(assessment: SafetyAssessment) -> SafetyOut:
    return SafetyOut(
        level=assessment.level,
        notices=[
            SafetyNoticeOut(
                level=n.level,  # type: ignore[arg-type]
                title=n.title,
                message=n.message,
                source_url=n.source_url,
                source_label=n.source_label,
            )
            for n in assessment.notices
        ],
    )


def _insufficient_text(language: Language) -> str:
    return {
        "en": (
            "I could not find this topic in SakhiSahay's current knowledge sources, so I will not guess. "
            "The sources I can draw on cover menstrual health, PCOS, endometriosis, menopause, pregnancy warning "
            "signs, contraception and sexual health. For anything personal or persistent, a gynaecologist or "
            "family doctor is the right person to ask."
        ),
        "hi": (
            "यह विषय SakhiSahay के मौजूदा स्रोतों में नहीं मिला, इसलिए मैं अनुमान नहीं लगाऊँगी। "
            "मेरे स्रोत माहवारी (periods), PCOS, एंडोमेट्रियोसिस, रजोनिवृत्ति (menopause), गर्भावस्था के चेतावनी संकेत, "
            "गर्भनिरोध और यौन स्वास्थ्य को कवर करते हैं। व्यक्तिगत या लगातार समस्या के लिए स्त्री रोग विशेषज्ञ या "
            "पारिवारिक डॉक्टर से मिलें।"
        ),
        "hinglish": (
            "Yeh topic SakhiSahay ke current sources mein nahi mila, isliye main guess nahi karungi. "
            "Mere sources periods, PCOS, endometriosis, menopause, pregnancy ke warning signs, contraception aur "
            "sexual health cover karte hain. Personal ya lagataar problem ke liye gynaecologist ya family doctor "
            "se milna sahi rahega."
        ),
    }[language]


def _retrieval_only_text(language: Language, chunks: list[ScoredChunk]) -> str:
    intro = {
        "en": "Live answer generation is unavailable, so here are the most relevant passages from SakhiSahay's cited sources, unchanged:",
        "hi": "अभी उत्तर तैयार करने वाला मॉडल उपलब्ध नहीं है, इसलिए नीचे SakhiSahay के स्रोतों से सबसे प्रासंगिक अंश (अंग्रेज़ी में, बिना बदलाव) दिए गए हैं:",
        "hinglish": "Abhi answer generate karne wala model available nahi hai, isliye neeche SakhiSahay ke sources se sabse relevant passages (English mein, bina badlav) diye gaye hain:",
    }[language]
    parts = [intro, ""]
    for i, chunk in enumerate(chunks[:3], start=1):
        p = chunk.payload
        section = f" - {p.section}" if p.section else ""
        parts.append(f"**{p.publisher}: {p.title}{section}** [S{i}]")
        parts.append("")
        parts.append(f"> {_excerpt(p.text)}")
        parts.append("")
    return "\n".join(parts).strip()


def answer_question(
    question: str,
    language_choice: LanguageChoice = "auto",
    tracker_context: str | None = None,
) -> ChatResponse:
    started = time.perf_counter()
    settings = get_settings()
    detected, language = resolve_language(question, language_choice)
    safety = screen_question(question)

    status = get_pipeline_status()
    if not status.get("index_ready"):
        raise KnowledgeIndexUnavailable("Knowledge index is empty. Run `python -m app.knowledge.ingest` first.")

    # Gate on the detected language: cross-lingual similarity is systematically lower.
    result: RetrievalResult = retrieve(question, language=detected)
    latency = lambda: int((time.perf_counter() - started) * 1000)  # noqa: E731
    common = {
        "language_detected": detected,
        "language_used": language,
        "safety": _safety_out(safety),
        "best_score": round(result.best_score, 3) if result.best_score is not None else None,
        "evidence_strength": evidence_strength(result.best_score, result.min_score),
        "disclaimer": EDUCATIONAL_DISCLAIMER,
        "tracker_context_used": bool(tracker_context),
    }

    if not result.chunks:
        return ChatResponse(
            answer=_insufficient_text(language),
            mode="insufficient_evidence",
            sources=_sources(result.weak, cited=[]),
            model=None,
            retrieved_count=0,
            latency_ms=latency(),
            fallback_reason=f"No passage scored above the relevance gate ({result.min_score:.2f}).",
            **common,
        )

    llm = get_llm()
    if llm is None:
        return ChatResponse(
            answer=_retrieval_only_text(language, result.chunks),
            mode="retrieval_only",
            sources=_sources(result.chunks, cited=list(range(1, min(3, len(result.chunks)) + 1))),
            model=None,
            retrieved_count=len(result.chunks),
            latency_ms=latency(),
            fallback_reason="No language-model provider configured (set GEMINI_API_KEY).",
            **common,
        )

    prompt = build_prompt(question, result.chunks, language, LANGUAGE_LABELS[language], tracker_context)
    try:
        generated = llm.generate(prompt.system, prompt.user)
    except LLMUnavailable as exc:
        log.warning("llm unavailable: %s", exc.reason)
        return ChatResponse(
            answer=_retrieval_only_text(language, result.chunks),
            mode="retrieval_only",
            sources=_sources(result.chunks, cited=list(range(1, min(3, len(result.chunks)) + 1))),
            model=llm.model,
            retrieved_count=len(result.chunks),
            latency_ms=latency(),
            fallback_reason=exc.reason,
            **common,
        )

    validated = validate_citations(generated.text, result.chunks)
    if validated.removed_markers or validated.removed_urls:
        log.info("citation validation removed %d markers, %d urls", validated.removed_markers, validated.removed_urls)
    log.info("answered in %dms (mode=llm, chunks=%d, cited=%d, lang=%s)", latency(), len(result.chunks), len(validated.cited_indices), language)
    return ChatResponse(
        answer=validated.text,
        mode="llm",
        sources=_sources(result.chunks, cited=validated.cited_indices),
        model=generated.model,
        retrieved_count=len(result.chunks),
        latency_ms=latency(),
        fallback_reason=None if validated.explicit else "The model did not cite passages explicitly; all retrieved sources are listed.",
        **common,
    )
