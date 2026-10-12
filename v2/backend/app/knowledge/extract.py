"""Text extraction and normalisation for HTML pages and PDFs."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedText:
    text: str
    method: str
    title: str | None = None
    date_hint: str | None = None
    warnings: list[str] = field(default_factory=list)


class ExtractionError(RuntimeError):
    pass


_BOILERPLATE_PATTERNS = [
    re.compile(r"^\s*(cookie|cookies)\b.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*share (this|on)\b.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*(print|download|subscribe)\s*$", re.IGNORECASE | re.MULTILINE),
]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"-\n(?=[a-z])", "", text)  # de-hyphenate PDF line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    for pattern in _BOILERPLATE_PATTERNS:
        text = pattern.sub("", text)
    return text.strip()


def extract_html(raw: bytes) -> ExtractedText:
    import trafilatura

    html = raw.decode("utf-8", errors="replace")
    text = None
    method = "trafilatura-markdown"
    try:
        text = trafilatura.extract(
            html,
            output_format="markdown",
            include_tables=True,
            include_links=False,
            include_comments=False,
            favor_recall=True,
        )
    except Exception:  # pragma: no cover - depends on library version
        text = None
    if not text:
        method = "trafilatura-txt"
        text = trafilatura.extract(html, include_tables=True, include_comments=False, favor_recall=True)
    if not text:
        raise ExtractionError("trafilatura returned no main content")

    title = None
    date_hint = None
    try:
        meta = trafilatura.extract_metadata(html)
        if meta is not None:
            title = meta.title
            date_hint = meta.date
    except Exception:  # pragma: no cover
        pass
    return ExtractedText(text=normalise(text), method=method, title=title, date_hint=date_hint)


def extract_pdf(path: Path) -> ExtractedText:
    import pymupdf

    warnings: list[str] = []
    parts: list[str] = []
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ExtractionError("PDF is password protected")
        for page_number, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            if not page_text.strip():
                warnings.append(f"page {page_number} had no extractable text (scanned image?)")
                continue
            parts.append(page_text)
        title = (doc.metadata or {}).get("title") or None
    if not parts:
        raise ExtractionError("PDF contained no extractable text")
    text = normalise("\n\n".join(parts))
    # Drop obvious running headers/footers: short lines that repeat many times.
    lines = text.split("\n")
    counts: dict[str, int] = {}
    for line in lines:
        key = line.strip()
        if 0 < len(key) <= 60:
            counts[key] = counts.get(key, 0) + 1
    repeated = {k for k, v in counts.items() if v >= 4}
    if repeated:
        lines = [ln for ln in lines if ln.strip() not in repeated]
        warnings.append(f"removed {len(repeated)} repeated header/footer lines")
    return ExtractedText(text="\n".join(lines).strip(), method="pymupdf", title=title, warnings=warnings)


def extract(path: Path, content_type: str) -> ExtractedText:
    if content_type == "pdf":
        return extract_pdf(path)
    return extract_html(path.read_bytes())
