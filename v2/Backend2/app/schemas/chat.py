"""
SakhiSahay RAG Backend — Pydantic schemas for the chat API.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's health question")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for future multi-turn support"
    )


class SourceDocument(BaseModel):
    title: str
    url: Optional[str] = None
    category: str
    page: Optional[int] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    sources: List[SourceDocument] = []
    insufficient_evidence: bool = False
    disclaimer: str = (
        "This information is educational and does not replace professional "
        "medical advice. Please consult a qualified healthcare professional "
        "for personal health concerns."
    )


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


class KBStatusResponse(BaseModel):
    collection: str
    total_chunks: int
    qdrant_mode: str
    embedding_model: str
    gemini_model: str
