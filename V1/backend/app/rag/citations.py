"""Citation validation.

The model may only reference evidence it was actually shown. Markers that do
not map to a retrieved passage are removed, URLs that are not among the
retrieved sources are stripped, and the final source list is built from the
retrieved chunks themselves, never from model output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.vector_store import ScoredChunk

MARKER_RE = re.compile(r"\[S(\d{1,2})\]")
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")


@dataclass
class ValidatedAnswer:
    text: str
    cited_indices: list[int]  # 1-based indices into the evidence list, in order of first use
    removed_markers: int
    removed_urls: int
    explicit: bool  # True when the model cited at least one valid marker


def validate_citations(answer: str, chunks: list[ScoredChunk]) -> ValidatedAnswer:
    allowed = set(range(1, len(chunks) + 1))
    allowed_urls = {c.payload.url.rstrip("/") for c in chunks}
    cited: list[int] = []
    removed_markers = 0

    def _marker(match: re.Match[str]) -> str:
        nonlocal removed_markers
        idx = int(match.group(1))
        if idx in allowed:
            if idx not in cited:
                cited.append(idx)
            return match.group(0)
        removed_markers += 1
        return ""

    text = MARKER_RE.sub(_marker, answer)

    removed_urls = 0

    def _url(match: re.Match[str]) -> str:
        nonlocal removed_urls
        if match.group(0).rstrip("/").rstrip(".") in allowed_urls:
            return match.group(0)
        removed_urls += 1
        return "[link removed: not among retrieved sources]"

    text = URL_RE.sub(_url, text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return ValidatedAnswer(
        text=text,
        cited_indices=cited,
        removed_markers=removed_markers,
        removed_urls=removed_urls,
        explicit=bool(cited),
    )
