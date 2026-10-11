"""
Document loader — extract raw text and metadata from PDF, TXT, and MD files.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RawDocument:
    """Represents a single loaded document before chunking."""

    file_path: str
    filename: str
    category: str                   # Derived from parent directory name
    title: str                      # Best-effort: first meaningful heading or filename stem
    source_org: str                 # e.g. "NHS", "ACOG", "WHO", "CDC"
    text: str
    total_pages: int = 1
    checksum: str = ""              # SHA-256 of raw file bytes
    pages: List[dict] = field(default_factory=list)  # [{page: int, text: str}]
    error: Optional[str] = None     # Non-None if extraction failed


# ── Source-organisation detection from filename ───────────────────────────────

_SOURCE_KEYWORDS = {
    "NHS": "NHS (National Health Service, UK)",
    "ACOG": "ACOG (American College of Obstetricians and Gynecologists)",
    "CDC": "CDC (Centers for Disease Control and Prevention)",
    "WHO": "WHO (World Health Organization)",
}


def _detect_source_org(filename: str) -> str:
    upper = filename.upper()
    for key, label in _SOURCE_KEYWORDS.items():
        if key in upper:
            return label
    # WHO ISBN-style PDFs
    if filename.startswith("978"):
        return "WHO (World Health Organization)"
    return "Unknown"


def _extract_title(filename: str, first_text: str) -> str:
    """
    Try to get a meaningful title from the filename stem first.
    NHS/ACOG files already have descriptive names.
    """
    stem = Path(filename).stem
    # Remove trailing suffixes like " - NHS", " _ ACOG"
    for suffix in [" - NHS", " _ ACOG", " _ CDC", " _ WHO", "-eng"]:
        stem = stem.replace(suffix, "")
    # If the stem looks like a plain ISBN (digits only), fall back to first line
    if stem.replace("-", "").isdigit():
        first_line = first_text.strip().split("\n")[0].strip()
        if first_line:
            return first_line[:120]
        return stem
    return stem.strip()


# ── PDF loader ────────────────────────────────────────────────────────────────

def _load_pdf(path: Path, category: str) -> RawDocument:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF (fitz) is not installed. Run: pip install pymupdf")

    raw_bytes = path.read_bytes()
    checksum = hashlib.sha256(raw_bytes).hexdigest()

    try:
        doc = fitz.open(path)
    except Exception as exc:
        return RawDocument(
            file_path=str(path),
            filename=path.name,
            category=category,
            title=path.stem,
            source_org=_detect_source_org(path.name),
            text="",
            checksum=checksum,
            error=f"Could not open PDF: {exc}",
        )

    pages: List[dict] = []
    full_text_parts: List[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")  # type: ignore[attr-defined]
        if page_text.strip():
            pages.append({"page": page_num + 1, "text": page_text})
            full_text_parts.append(page_text)

    doc.close()

    full_text = "\n".join(full_text_parts)

    if not full_text.strip():
        return RawDocument(
            file_path=str(path),
            filename=path.name,
            category=category,
            title=path.stem,
            source_org=_detect_source_org(path.name),
            text="",
            total_pages=len(pages),
            checksum=checksum,
            pages=pages,
            error="No extractable text found. This may be a scanned PDF requiring OCR.",
        )

    title = _extract_title(path.name, full_text)
    source_org = _detect_source_org(path.name)

    return RawDocument(
        file_path=str(path),
        filename=path.name,
        category=category,
        title=title,
        source_org=source_org,
        text=full_text,
        total_pages=len(pages),
        checksum=checksum,
        pages=pages,
    )


def _load_text(path: Path, category: str) -> RawDocument:
    raw_bytes = path.read_bytes()
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    text = raw_bytes.decode("utf-8", errors="replace")
    title = _extract_title(path.name, text)
    return RawDocument(
        file_path=str(path),
        filename=path.name,
        category=category,
        title=title,
        source_org=_detect_source_org(path.name),
        text=text,
        checksum=checksum,
        pages=[{"page": 1, "text": text}],
    )


# ── Public interface ──────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def load_document(path: Path) -> RawDocument:
    """Load a single file and return a RawDocument."""
    category = path.parent.name  # directory name = category
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _load_pdf(path, category)
    elif ext in {".txt", ".md"}:
        return _load_text(path, category)
    else:
        return RawDocument(
            file_path=str(path),
            filename=path.name,
            category=category,
            title=path.stem,
            source_org="Unknown",
            text="",
            error=f"Unsupported file type: {ext}",
        )


def discover_documents(raw_dir: Path) -> List[Path]:
    """Recursively find all supported documents under raw_dir."""
    found: List[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        found.extend(raw_dir.rglob(f"*{ext}"))
    return sorted(found)
