"""Polite, cached document acquisition.

Raw HTML/PDF responses are cached under data/knowledge/cache (git-ignored) so
re-running ingestion does not re-hit publishers. Extracted text snapshots are
kept alongside (committed) so the demo is reproducible offline.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

USER_AGENT = "SakhiSahay-academic-project/0.1 (+student research; contact via repository)"
REQUEST_DELAY_SECONDS = 1.0


@dataclass
class AcquiredDocument:
    source_id: str
    url: str
    content_type: str  # "html" | "pdf"
    path: Path
    accessed_date: str
    from_cache: bool
    http_status: int | None


class AcquisitionError(RuntimeError):
    pass


def _guess_type(url: str, header: str | None) -> str:
    header = (header or "").lower()
    if "pdf" in header or url.lower().endswith(".pdf"):
        return "pdf"
    return "html"


def acquire(source_id: str, url: str, cache_dir: Path, refresh: bool = False) -> AcquiredDocument:
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cache_dir / f"{source_id}.fetch.json"

    if not refresh and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cached = cache_dir / meta["file"]
        if cached.exists():
            return AcquiredDocument(
                source_id=source_id,
                url=url,
                content_type=meta["content_type"],
                path=cached,
                accessed_date=meta["accessed_date"],
                from_cache=True,
                http_status=meta.get("http_status"),
            )

    time.sleep(REQUEST_DELAY_SECONDS)
    try:
        with httpx.Client(follow_redirects=True, timeout=45.0, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        raise AcquisitionError(f"Network error fetching {url}: {exc.__class__.__name__}") from exc

    if response.status_code != 200:
        raise AcquisitionError(f"HTTP {response.status_code} fetching {url}")

    content_type = _guess_type(url, response.headers.get("content-type"))
    file_name = f"{source_id}.{content_type}"
    (cache_dir / file_name).write_bytes(response.content)
    accessed = date.today().isoformat()
    meta_path.write_text(
        json.dumps(
            {
                "file": file_name,
                "content_type": content_type,
                "accessed_date": accessed,
                "http_status": response.status_code,
                "final_url": str(response.url),
                "bytes": len(response.content),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return AcquiredDocument(
        source_id=source_id,
        url=url,
        content_type=content_type,
        path=cache_dir / file_name,
        accessed_date=accessed,
        from_cache=False,
        http_status=response.status_code,
    )
