from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, HttpUrl


class SourceSpec(BaseModel):
    id: str
    title: str
    publisher: str
    url: HttpUrl
    landing_url: HttpUrl | None = None
    doc_type: str
    topic: str
    language: str = "en"
    published_date: str | None = None
    updated_date: str | None = None
    license_note: str | None = None
    min_chars: int = 800


class Manifest(BaseModel):
    sources: list[SourceSpec]

    def by_id(self) -> dict[str, SourceSpec]:
        return {s.id: s for s in self.sources}


def load_manifest(path: Path) -> Manifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = raw.get("defaults") or {}
    sources = []
    seen: set[str] = set()
    for item in raw.get("sources", []):
        merged = {**defaults, **item}
        spec = SourceSpec(**merged)
        if spec.id in seen:
            raise ValueError(f"Duplicate source id in manifest: {spec.id}")
        seen.add(spec.id)
        sources.append(spec)
    return Manifest(sources=sources)
