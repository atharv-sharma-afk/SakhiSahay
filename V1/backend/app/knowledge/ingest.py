"""Knowledge-base ingestion CLI.

    python -m app.knowledge.ingest            # fetch (cached), extract, chunk, embed, index
    python -m app.knowledge.ingest --rebuild  # drop and recreate the vector collection
    python -m app.knowledge.ingest --refresh  # re-download sources instead of using the cache
    python -m app.knowledge.ingest --only who-pcos nhs-heavy-periods

Ingestion is deliberately separate from the chat pipeline. It writes:
  * data/knowledge/cache/<id>.txt       extracted text snapshot (committed)
  * data/knowledge/cache/<id>.meta.json extraction report (committed)
  * the Qdrant collection (runtime, git-ignored)
  * the knowledge_sources table (status indexed|failed with detail)

Run it before starting the API when using embedded Qdrant: the local store is
single-process.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db import models
from app.db.init_db import init_db
from app.db.session import get_sessionmaker
from app.knowledge.acquire import AcquisitionError, acquire
from app.knowledge.chunk import chunk_text
from app.knowledge.extract import ExtractionError, extract
from app.knowledge.manifest import SourceSpec, load_manifest
from app.logging_config import configure_logging
from app.rag.embeddings import get_embedder
from app.rag.vector_store import ChunkPayload, get_vector_store

log = logging.getLogger("sakhisahay.ingest")


def _write_snapshot(cache_dir: Path, spec: SourceSpec, text: str, report: dict) -> None:
    (cache_dir / f"{spec.id}.txt").write_text(text, encoding="utf-8")
    (cache_dir / f"{spec.id}.meta.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def _upsert_registry(session, spec: SourceSpec, **fields) -> None:
    row = session.get(models.KnowledgeSource, spec.id)
    if row is None:
        row = models.KnowledgeSource(id=spec.id)
        session.add(row)
    row.title = spec.title
    row.publisher = spec.publisher
    row.url = str(spec.url)
    row.doc_type = spec.doc_type
    row.topic = spec.topic
    row.language = spec.language
    row.published_date = spec.published_date
    row.updated_date = spec.updated_date
    row.license_note = spec.license_note
    for key, value in fields.items():
        setattr(row, key, value)
    session.commit()


def ingest(only: list[str] | None = None, rebuild: bool = False, refresh: bool = False, offline: bool = False) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    manifest = load_manifest(settings.knowledge_dir / "sources.yaml")
    cache_dir = settings.knowledge_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    embedder = get_embedder()
    store = get_vector_store()
    store.ensure_collection(embedder.dimension, recreate=rebuild)

    selected = [s for s in manifest.sources if not only or s.id in set(only)]
    failures = 0
    with get_sessionmaker()() as session:
        for spec in selected:
            log.info("[%s] acquiring", spec.id)
            try:
                snapshot = cache_dir / f"{spec.id}.txt"
                if offline and snapshot.exists():
                    text = snapshot.read_text(encoding="utf-8")
                    meta = json.loads((cache_dir / f"{spec.id}.meta.json").read_text(encoding="utf-8"))
                    accessed = meta.get("accessed_date")
                    report = meta
                else:
                    doc = acquire(spec.id, str(spec.url), cache_dir, refresh=refresh)
                    extracted = extract(doc.path, doc.content_type)
                    text = extracted.text
                    accessed = doc.accessed_date
                    report = {
                        "source_id": spec.id,
                        "url": str(spec.url),
                        "accessed_date": accessed,
                        "content_type": doc.content_type,
                        "extraction_method": extracted.method,
                        "page_title": extracted.title,
                        "date_hint": extracted.date_hint,
                        "char_count": len(text),
                        "warnings": extracted.warnings,
                    }
                if len(text) < spec.min_chars:
                    raise ExtractionError(f"only {len(text)} characters extracted (< {spec.min_chars}); treating as malformed")

                chunks = chunk_text(text)
                report["chunk_count"] = len(chunks)
                _write_snapshot(cache_dir, spec, text, report)

                payloads = [
                    ChunkPayload(
                        chunk_id=f"{spec.id}::{c.index:03d}",
                        source_id=spec.id,
                        title=spec.title,
                        publisher=spec.publisher,
                        url=str(spec.url),
                        doc_type=spec.doc_type,
                        topic=spec.topic,
                        section=c.section,
                        language=spec.language,
                        published_date=spec.published_date,
                        updated_date=spec.updated_date or report.get("date_hint"),
                        accessed_date=accessed,
                        license_note=spec.license_note,
                        text=c.text,
                    )
                    for c in chunks
                ]
                vectors = embedder.embed_passages([p.text for p in payloads])
                store.delete_source(spec.id)
                store.upsert(payloads, vectors)
                _upsert_registry(
                    session,
                    spec,
                    accessed_date=accessed,
                    chunk_count=len(chunks),
                    status="indexed",
                    status_detail=None,
                    ingested_at=datetime.now(timezone.utc),
                )
                log.info("[%s] indexed %d chunks (%d chars)", spec.id, len(chunks), len(text))
            except (AcquisitionError, ExtractionError) as exc:
                failures += 1
                log.error("[%s] FAILED: %s", spec.id, exc)
                _upsert_registry(session, spec, status="failed", status_detail=str(exc), chunk_count=0)
            except Exception as exc:  # noqa: BLE001 - report and continue with other sources
                failures += 1
                log.exception("[%s] unexpected failure", spec.id)
                _upsert_registry(session, spec, status="failed", status_detail=f"{type(exc).__name__}: {exc}", chunk_count=0)

        indexed = session.scalars(select(models.KnowledgeSource).where(models.KnowledgeSource.status == "indexed")).all()
        log.info("done: %d indexed, %d failed, %d total chunks", len(indexed), failures, sum(s.chunk_count for s in indexed))
    return 1 if failures and failures == len(selected) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the SakhiSahay knowledge index")
    parser.add_argument("--only", nargs="*", help="source ids to (re)ingest")
    parser.add_argument("--rebuild", action="store_true", help="recreate the vector collection")
    parser.add_argument("--refresh", action="store_true", help="re-download instead of using cached responses")
    parser.add_argument("--offline", action="store_true", help="use committed text snapshots; never touch the network")
    args = parser.parse_args(argv)
    return ingest(only=args.only, rebuild=args.rebuild, refresh=args.refresh, offline=args.offline)


if __name__ == "__main__":
    sys.exit(main())
