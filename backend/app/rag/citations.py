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
    insufficient_evidence: bool = False


@dataclass
class ParsedModelOutput:
    answer: str
    insufficient_evidence: bool
    source_ids: list[str]


def parse_model_response(raw_text: str) -> ParsedModelOutput:
    """Parse the structured return format from the compact prompt:
    ANSWER: ...
    INSUFFICIENT_EVIDENCE: true|false
    SOURCE_IDS: ...
    """
    raw = (raw_text or "").strip()
    insufficient = False
    source_ids: list[str] = []

    m_insuf = re.search(r"INSUFFICIENT_EVIDENCE:\s*(true|false)", raw, re.IGNORECASE)
    if m_insuf:
        insufficient = m_insuf.group(1).lower() == "true"

    m_src = re.search(r"SOURCE_IDS:\s*([^\r\n]+)", raw, re.IGNORECASE)
    if m_src:
        val = m_src.group(1).strip()
        s_matches = re.findall(r"\[?S?(\d+)\]?", val, re.IGNORECASE)
        if s_matches:
            source_ids = [f"S{num}" for num in s_matches if num != "0"]
        elif val.lower() not in ("none", "n/a", "[]", "", "false"):
            for part in val.split(","):
                cleaned = part.strip(" []'\"")
                if cleaned:
                    source_ids.append(cleaned)

    m_ans = re.search(r"ANSWER:\s*(.*?)(?=\n(?:INSUFFICIENT_EVIDENCE|SOURCE_IDS):|\Z)", raw, re.DOTALL | re.IGNORECASE)
    if m_ans:
        answer = m_ans.group(1).strip()
    else:
        lines = []
        for line in raw.splitlines():
            if re.match(r"^\s*(INSUFFICIENT_EVIDENCE|SOURCE_IDS):", line, re.IGNORECASE):
                continue
            lines.append(line)
        answer = "\n".join(lines).strip()

    return ParsedModelOutput(
        answer=answer,
        insufficient_evidence=insufficient,
        source_ids=source_ids,
    )


def validate_citations(
    answer: str,
    chunks: list[ScoredChunk],
    declared_source_ids: list[str] | None = None,
) -> ValidatedAnswer:
    allowed = set(range(1, len(chunks) + 1))
    source_id_to_idx = {c.payload.source_id: i for i, c in enumerate(chunks, start=1)}
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

    # Also incorporate declared source IDs from SOURCE_IDS line if valid
    if declared_source_ids:
        for sid in declared_source_ids:
            num_match = re.search(r"(\d+)", sid)
            if num_match:
                idx = int(num_match.group(1))
                if idx in allowed and idx not in cited:
                    cited.append(idx)
            elif sid in source_id_to_idx:
                idx = source_id_to_idx[sid]
                if idx not in cited:
                    cited.append(idx)

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

