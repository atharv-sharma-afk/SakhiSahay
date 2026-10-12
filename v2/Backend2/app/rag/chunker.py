"""
Text chunker — split cleaned documents into overlapping chunks.

Strategy:
  - Split text on paragraph boundaries (\n\n) first.
  - Accumulate paragraphs until the target token budget is reached.
  - When the budget is reached, emit a chunk and slide back by ~overlap tokens.
  - Never split inside a sentence if avoidable.
  - Token count approximated as: len(words) / 0.75 (fast, no tokenizer needed).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings
from app.rag.document_loader import RawDocument


@dataclass
class Chunk:
    """A single text chunk ready for embedding."""

    chunk_id: str            # Stable deterministic ID
    text: str
    filename: str
    title: str
    category: str
    source_org: str
    page_start: Optional[int]
    page_end: Optional[int]
    chunk_index: int         # 0-based index within its source document
    total_chunks: int        # How many chunks this document produced
    checksum: str            # Parent document checksum (for incremental updates)


# ── Token approximation ───────────────────────────────────────────────────────

def _approx_tokens(text: str) -> int:
    """Approximate token count (words × 1.33 is close enough for chunking)."""
    return max(1, int(len(text.split()) / 0.75))


# ── Chunk ID generation ───────────────────────────────────────────────────────

def _make_chunk_id(filename: str, chunk_index: int, text: str) -> str:
    """Create a stable deterministic ID for a chunk."""
    key = f"{filename}::{chunk_index}::{text[:64]}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]


# ── Paragraph-aware splitter ──────────────────────────────────────────────────

def _split_paragraphs(text: str) -> List[str]:
    """Split text on blank lines, preserving non-empty paragraphs."""
    paragraphs = re.split(r"\n\n+", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_document(
    doc: RawDocument,
    chunk_size: int = None,
    overlap: int = None,
) -> List[Chunk]:
    """
    Chunk a RawDocument into overlapping text chunks.

    Args:
        doc:        The raw document to chunk.
        chunk_size: Target size in tokens (defaults to settings.chunk_size_tokens).
        overlap:    Token overlap between consecutive chunks (defaults to settings.chunk_overlap_tokens).

    Returns:
        List of Chunk objects, or empty list if document has no text.
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size_tokens
    if overlap is None:
        overlap = settings.chunk_overlap_tokens

    if not doc.text.strip():
        return []

    paragraphs = _split_paragraphs(doc.text)
    if not paragraphs:
        return []

    chunks_text: List[str] = []
    current_parts: List[str] = []
    current_tokens: int = 0

    for para in paragraphs:
        para_tokens = _approx_tokens(para)

        # If a single paragraph exceeds the chunk limit, split on sentence boundaries
        if para_tokens > chunk_size:
            # Flush current buffer first
            if current_parts:
                chunks_text.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0

            # Split large paragraph on sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                sent_tokens = _approx_tokens(sent)
                if current_tokens + sent_tokens > chunk_size and current_parts:
                    chunks_text.append(" ".join(current_parts))
                    # Keep overlap by retaining the last N words
                    overlap_words = int(overlap * 0.75)
                    retained = " ".join(" ".join(current_parts).split()[-overlap_words:])
                    current_parts = [retained] if retained else []
                    current_tokens = _approx_tokens(retained)
                current_parts.append(sent)
                current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > chunk_size and current_parts:
                chunks_text.append("\n\n".join(current_parts))
                # Slide back by overlap
                overlap_words = int(overlap * 0.75)
                last_text = "\n\n".join(current_parts)
                retained = " ".join(last_text.split()[-overlap_words:])
                current_parts = [retained] if retained else []
                current_tokens = _approx_tokens(retained)

            current_parts.append(para)
            current_tokens += para_tokens

    # Flush any remaining content
    if current_parts:
        chunks_text.append("\n\n".join(current_parts))

    # ── Build Chunk objects ───────────────────────────────────────────────────
    total = len(chunks_text)
    result: List[Chunk] = []

    for idx, text in enumerate(chunks_text):
        if not text.strip():
            continue
        chunk_id = _make_chunk_id(doc.filename, idx, text)
        result.append(
            Chunk(
                chunk_id=chunk_id,
                text=text,
                filename=doc.filename,
                title=doc.title,
                category=doc.category,
                source_org=doc.source_org,
                page_start=None,
                page_end=None,
                chunk_index=idx,
                total_chunks=total,
                checksum=doc.checksum,
            )
        )

    return result
