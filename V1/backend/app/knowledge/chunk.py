"""Heading-aware chunking.

Text is split into paragraphs; markdown headings update the current section
label; paragraphs are packed into chunks of roughly `max_chars` with a one
paragraph overlap so sentences that straddle a boundary remain retrievable.
Sizes are in characters because they are language-neutral and keep every
chunk comfortably inside the 512-token window of the embedding models used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
MAX_CHARS_DEFAULT = 1100
MIN_CHARS_DEFAULT = 200


@dataclass
class Chunk:
    index: int
    section: str | None
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?।])\s+", paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_chars and current:
            pieces.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current.strip())
    return pieces


def chunk_text(
    text: str,
    max_chars: int = MAX_CHARS_DEFAULT,
    min_chars: int = MIN_CHARS_DEFAULT,
) -> list[Chunk]:
    paragraphs_raw = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[Chunk] = []
    section: str | None = None
    buffer: list[str] = []
    buffer_section: str | None = None
    carry: list[str] = []  # fragments too small to stand alone; prepended to the next chunk

    def flush() -> None:
        nonlocal buffer, carry
        if not buffer:
            return
        body = "\n\n".join([*carry, *buffer]).strip()
        if len(body) < min_chars:
            carry = [*carry, *buffer]
        else:
            chunks.append(Chunk(index=len(chunks), section=buffer_section, text=body))
            carry = []
        buffer = []

    for paragraph in paragraphs_raw:
        heading = HEADING_RE.match(paragraph)
        if heading:
            flush()
            section = heading.group(2).strip() or None
            buffer_section = section
            continue
        if buffer_section != section and buffer:
            flush()
        buffer_section = section
        pieces = [paragraph] if len(paragraph) <= max_chars else _split_long_paragraph(paragraph, max_chars)
        for piece in pieces:
            projected = sum(len(p) for p in buffer) + len(piece) + 2 * len(buffer)
            if projected > max_chars and buffer:
                overlap = buffer[-1]
                flush()
                if len(overlap) < max_chars // 3:
                    buffer = [overlap]
            buffer.append(piece)
    flush()
    if carry:
        leftover = "\n\n".join(carry).strip()
        if chunks:
            chunks[-1].text = f"{chunks[-1].text}\n\n{leftover}"
        elif leftover:
            chunks.append(Chunk(index=0, section=buffer_section, text=leftover))
    for i, c in enumerate(chunks):
        c.index = i
    return chunks
