"""
Document ingestion pipeline — orchestrates Discover → Extract → Clean → Chunk → Embed → Index.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.rag.chunker import chunk_document
from app.rag.document_loader import discover_documents, load_document
from app.rag.embeddings import embed_texts
from app.rag.text_cleaner import clean_text
from app.rag.vector_store import delete_by_filename, ensure_collection, upsert_chunks

logger = logging.getLogger(__name__)


# ── Manifest (tracks what's been indexed) ────────────────────────────────────

@dataclass
class ManifestEntry:
    filename: str
    checksum: str
    chunks_count: int
    ingested_at: str
    category: str
    title: str


def _load_manifest(path: Path) -> Dict[str, ManifestEntry]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: ManifestEntry(**v) for k, v in data.items()}
    except Exception as e:
        logger.warning("Could not load manifest (%s). Starting fresh.", e)
        return {}


def _save_manifest(path: Path, manifest: Dict[str, ManifestEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({k: asdict(v) for k, v in manifest.items()}, indent=2),
        encoding="utf-8",
    )


# ── Ingestion report ──────────────────────────────────────────────────────────

@dataclass
class IngestionReport:
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    chunks_created: int = 0
    chunks_deleted: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return self.processed + self.skipped + self.failed


# ── Single-document ingestion ─────────────────────────────────────────────────

def ingest_file(
    path: Path,
    manifest: Dict[str, ManifestEntry],
    force: bool = False,
) -> IngestionReport:
    """
    Ingest a single file into Qdrant.

    Args:
        path:     Path to the file.
        manifest: Current manifest dict (will be modified in place).
        force:    If True, re-ingest even if checksum matches.

    Returns:
        IngestionReport for this single file.
    """
    report = IngestionReport()
    filename = path.name

    # 1. Load document (extract text + metadata)
    raw_doc = load_document(path)

    if raw_doc.error:
        logger.warning("[SKIP] %s — %s", filename, raw_doc.error)
        report.failed += 1
        report.errors.append(f"{filename}: {raw_doc.error}")
        return report

    if not raw_doc.text.strip():
        logger.warning("[SKIP] %s — empty text", filename)
        report.failed += 1
        report.errors.append(f"{filename}: No text content extracted")
        return report

    # 2. Check if unchanged (incremental ingestion)
    existing = manifest.get(filename)
    if not force and existing and existing.checksum == raw_doc.checksum:
        logger.info("[SKIP] %s — unchanged (checksum match)", filename)
        report.skipped += 1
        return report

    # 3. If file was previously indexed, delete old chunks first
    if existing:
        logger.info("[UPDATE] %s — deleting old chunks", filename)
        delete_by_filename(filename)

    # 4. Clean text
    raw_doc.text = clean_text(raw_doc.text)

    # 5. Chunk
    chunks = chunk_document(raw_doc)
    if not chunks:
        logger.warning("[SKIP] %s — produced 0 chunks after processing", filename)
        report.failed += 1
        report.errors.append(f"{filename}: No chunks produced")
        return report

    # 6. Embed
    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)

    if len(vectors) != len(chunks):
        report.failed += 1
        report.errors.append(f"{filename}: Embedding count mismatch")
        return report

    # 7. Upsert into Qdrant
    n_upserted = upsert_chunks(chunks, vectors)

    # 8. Update manifest
    manifest[filename] = ManifestEntry(
        filename=filename,
        checksum=raw_doc.checksum,
        chunks_count=n_upserted,
        ingested_at=datetime.now(timezone.utc).isoformat(),
        category=raw_doc.category,
        title=raw_doc.title,
    )

    logger.info(
        "[OK] %s — %d chunks indexed (category: %s)",
        filename,
        n_upserted,
        raw_doc.category,
    )
    report.processed += 1
    report.chunks_created += n_upserted
    return report


# ── Batch ingestion ───────────────────────────────────────────────────────────

def ingest_all(
    raw_dir: Path = None,
    manifest_path: Path = None,
    single_file: Optional[Path] = None,
    force: bool = False,
) -> IngestionReport:
    """
    Ingest all documents (or a single specified file) into Qdrant.

    Args:
        raw_dir:       Root directory containing categorised documents.
        manifest_path: Path to the manifest JSON file.
        single_file:   If set, only ingest this file.
        force:         Re-ingest even if checksums match.

    Returns:
        Aggregated IngestionReport.
    """
    if raw_dir is None:
        raw_dir = settings.data_raw_dir
    if manifest_path is None:
        manifest_path = settings.manifest_path

    # Ensure Qdrant collection exists
    ensure_collection()

    manifest = _load_manifest(manifest_path)
    total_report = IngestionReport()

    if single_file:
        paths = [single_file]
    else:
        paths = discover_documents(raw_dir)

    logger.info("Found %d file(s) to process.", len(paths))

    for path in paths:
        try:
            r = ingest_file(path, manifest, force=force)
            total_report.processed += r.processed
            total_report.skipped += r.skipped
            total_report.failed += r.failed
            total_report.chunks_created += r.chunks_created
            total_report.errors.extend(r.errors)
        except Exception as exc:
            logger.exception("Unexpected error processing %s: %s", path.name, exc)
            total_report.failed += 1
            total_report.errors.append(f"{path.name}: {exc}")

    _save_manifest(manifest_path, manifest)
    return total_report
