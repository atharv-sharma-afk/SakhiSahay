"""
Text cleaner — normalise raw extracted text before chunking.
"""
from __future__ import annotations

import re


# ── Public API ────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Apply a series of cleaning steps to raw extracted text.
    Preserves paragraph structure, headings, and list items.
    """
    if not text:
        return ""

    # 1. Normalise Windows/Mac line-endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Remove form-feed characters (PDF page separators)
    text = text.replace("\f", "\n\n")

    # 3. Remove null bytes and other control characters (except \n and \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)

    # 4. Remove PDF extraction artifacts: lone hyphen-continuation lines
    # e.g. "func-\ntion" → "function"
    text = re.sub(r"-\n(?=[a-z])", "", text)

    # 5. Collapse more than 2 consecutive blank lines into exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 6. Collapse excessive spaces/tabs within a single line (not across lines)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Collapse internal whitespace but keep indentation to 1 space
        cleaned = re.sub(r"[ \t]{2,}", " ", line).strip()
        cleaned_lines.append(cleaned)
    text = "\n".join(cleaned_lines)

    # 7. Remove repeated punctuation (e.g. "......" → "…")
    text = re.sub(r"\.{4,}", "…", text)

    # 8. Final strip
    return text.strip()
