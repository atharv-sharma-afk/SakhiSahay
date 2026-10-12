from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.rag.language import Language, LanguageChoice

ResponseMode = Literal["llm", "retrieval_only", "insufficient_evidence"]


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    language: LanguageChoice = "auto"
    # Explicit, per-request consent to include a numeric summary of the user's own
    # tracker records (no notes). Off by default.
    include_tracker_context: bool = False


class SourceRef(BaseModel):
    ref: int
    source_id: str
    title: str
    publisher: str
    url: str
    doc_type: str
    topic: str
    section: str | None
    excerpt: str
    score: float
    accessed_date: str | None
    updated_date: str | None
    cited: bool


class SafetyNoticeOut(BaseModel):
    level: Literal["advisory", "urgent"]
    title: str
    message: str
    source_url: str | None = None
    source_label: str | None = None


class SafetyOut(BaseModel):
    level: Literal["none", "advisory", "urgent"]
    notices: list[SafetyNoticeOut]


class ChatResponse(BaseModel):
    answer: str
    mode: ResponseMode
    language_detected: Language
    language_used: Language
    sources: list[SourceRef]
    safety: SafetyOut
    model: str | None
    retrieved_count: int
    best_score: float | None
    evidence_strength: Literal["none", "weak", "moderate", "strong"]
    latency_ms: int
    fallback_reason: str | None = None
    tracker_context_used: bool = False
    disclaimer: str
