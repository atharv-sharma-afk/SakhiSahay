"""
Local PDF ingestion script for SakhiSahay.

Reads PDFs directly from the dataset folder (no network required).
Run ONCE before starting the API:

    python ingest_local.py

Or with a rebuild (drop and recreate the vector collection):
    python ingest_local.py --rebuild
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Add the backend dir to Python path so 'app' module resolves.
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.db.init_db import init_db
from app.db.session import get_sessionmaker
from app.knowledge.chunk import chunk_text
from app.knowledge.extract import ExtractionError, extract_pdf
from app.logging_config import configure_logging
from app.rag.embeddings import get_embedder
from app.rag.vector_store import ChunkPayload, get_vector_store

log = logging.getLogger("sakhisahay.ingest_local")

# ────────────────────────────────────────────────────────────────────────────
# Dataset PDFs → metadata mapping
# topic values must match pipeline.py language / gate logic
# ────────────────────────────────────────────────────────────────────────────
DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"

PDF_MANIFEST: list[dict] = [
    # Menstrual health
    {"file": "Painful Periods _ ACOG.pdf",            "id": "acog-painful-periods",    "title": "Painful Periods",                              "publisher": "ACOG",  "topic": "menstrual_health",     "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/dysmenorrhea-painful-periods"},
    {"file": "Heavy and Abnormal Periods _ ACOG.pdf", "id": "acog-heavy-periods",      "title": "Heavy and Abnormal Periods",                   "publisher": "ACOG",  "topic": "menstrual_health",     "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/heavy-menstrual-bleeding"},
    {"file": "Amenorrhea_ Absence of Periods _ ACOG.pdf", "id": "acog-amenorrhea",    "title": "Amenorrhea – Absence of Periods",              "publisher": "ACOG",  "topic": "menstrual_health",     "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/amenorrhea"},
    {"file": "Premenstrual Syndrome (PMS) _ ACOG.pdf","id": "acog-pms",               "title": "Premenstrual Syndrome (PMS)",                  "publisher": "ACOG",  "topic": "menstrual_health",     "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/premenstrual-syndrome"},
    {"file": "Your First Period _ ACOG.pdf",          "id": "acog-first-period",       "title": "Your First Period",                            "publisher": "ACOG",  "topic": "menstrual_health",     "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/your-first-period"},
    {"file": "Period pain - NHS.pdf",                 "id": "nhs-period-pain",         "title": "Period Pain",                                  "publisher": "NHS",   "topic": "menstrual_health",     "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/period-pain/"},
    {"file": "Perimenopausal Bleeding and Bleeding After Menopause _ ACOG.pdf", "id": "acog-perimenopausal-bleeding", "title": "Perimenopausal Bleeding and Bleeding After Menopause", "publisher": "ACOG", "topic": "menstrual_health", "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/perimenopausal-bleeding"},

    # Pain relief
    {"file": "Naproxen_ a painkiller that also treats inflammation - NHS.pdf", "id": "nhs-naproxen", "title": "Naproxen – Painkiller for Inflammation", "publisher": "NHS", "topic": "menstrual_health", "doc_type": "patient_education", "url": "https://www.nhs.uk/medicines/naproxen/"},
    {"file": "TENS (transcutaneous electrical nerve stimulation) - NHS.pdf",  "id": "nhs-tens",     "title": "TENS – Transcutaneous Electrical Nerve Stimulation", "publisher": "NHS", "topic": "menstrual_health", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/tens/"},

    # PCOS & Endometriosis
    {"file": "Polycystic Ovary Syndrome (PCOS) _ ACOG.pdf", "id": "acog-pcos",        "title": "Polycystic Ovary Syndrome (PCOS)",              "publisher": "ACOG",  "topic": "pcos",                 "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/polycystic-ovary-syndrome"},
    {"file": "Polyendocrine metabolic ovarian syndrome (PMOS) - NHS.pdf",    "id": "nhs-pcos",  "title": "PCOS – NHS Overview",                  "publisher": "NHS",   "topic": "pcos",                 "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/polycystic-ovary-syndrome-pcos/"},
    {"file": "Excessive hair growth (hirsutism) - NHS.pdf",                   "id": "nhs-hirsutism", "title": "Excessive Hair Growth (Hirsutism)", "publisher": "NHS",  "topic": "pcos",                 "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/hirsutism/"},
    {"file": "Endometriosis - NHS.pdf",                                       "id": "nhs-endometriosis", "title": "Endometriosis – NHS Guide",    "publisher": "NHS",   "topic": "endometriosis",        "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/endometriosis/"},
    {"file": "Endometriosis _ ACOG.pdf",                                      "id": "acog-endometriosis", "title": "Endometriosis",             "publisher": "ACOG",   "topic": "endometriosis",        "doc_type": "patient_education", "url": "https://www.acog.org/womens-health/faqs/endometriosis"},
    {"file": "Adenomyosis - NHS.pdf",                                         "id": "nhs-adenomyosis", "title": "Adenomyosis – NHS Guide",      "publisher": "NHS",    "topic": "endometriosis",        "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/adenomyosis/"},

    # Menopause
    {"file": "Menopause and perimenopause - NHS.pdf",                         "id": "nhs-menopause",              "title": "Menopause and Perimenopause",           "publisher": "NHS",  "topic": "menopause", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/menopause/"},
    {"file": "Symptoms of menopause and perimenopause - NHS.pdf",             "id": "nhs-menopause-symptoms",     "title": "Symptoms of Menopause",                "publisher": "NHS",  "topic": "menopause", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/menopause/symptoms/"},
    {"file": "Things you can do to help menopause and perimenopause symptoms - NHS.pdf", "id": "nhs-menopause-selfcare", "title": "Self-Care for Menopause Symptoms", "publisher": "NHS", "topic": "menopause", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/menopause/things-you-can-do/"},
    {"file": "Treatment for menopause and perimenopause - NHS.pdf",           "id": "nhs-menopause-treatment",    "title": "Treatment for Menopause",              "publisher": "NHS",  "topic": "menopause", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/menopause/treatment/"},
    {"file": "What are menopause and perimenopause_ - NHS.pdf",               "id": "nhs-menopause-overview",     "title": "What is Menopause – NHS Overview",     "publisher": "NHS",  "topic": "menopause", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/menopause/what-is-it/"},

    # Reproductive health
    {"file": "Common Reproductive Health Concerns for Women _ Reproductive Health _ CDC.pdf", "id": "cdc-repro-concerns", "title": "Common Reproductive Health Concerns", "publisher": "CDC", "topic": "reproductive_health", "doc_type": "fact_sheet", "url": "https://www.cdc.gov/reproductivehealth/womensrh/"},
    {"file": "Women's Reproductive Health _ Reproductive Health _ CDC.pdf",  "id": "cdc-repro-overview",   "title": "Women's Reproductive Health",          "publisher": "CDC",  "topic": "reproductive_health", "doc_type": "fact_sheet", "url": "https://www.cdc.gov/reproductivehealth/womensrh/"},
    {"file": "Fibroids - NHS.pdf",                                            "id": "nhs-fibroids",         "title": "Fibroids – NHS Guide",                 "publisher": "NHS",  "topic": "reproductive_health", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/fibroids/"},
    {"file": "Pelvic inflammatory disease - NHS.pdf",                         "id": "nhs-pid",              "title": "Pelvic Inflammatory Disease",          "publisher": "NHS",  "topic": "reproductive_health", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/pelvic-inflammatory-disease-pid/"},

    # Contraception / IUD
    {"file": "What is an IUD (intrauterine device) or copper coil_ - NHS.pdf",                       "id": "nhs-iud-what",     "title": "What is an IUD / Copper Coil?",                 "publisher": "NHS", "topic": "contraception", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/contraception/iud-copper-coil/"},
    {"file": "Getting an IUD (intrauterine device) or copper coil fitted or removed - NHS.pdf",       "id": "nhs-iud-fitting",  "title": "Getting an IUD Fitted or Removed",              "publisher": "NHS", "topic": "contraception", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/contraception/iud-copper-coil/fitting-and-removal/"},
    {"file": "Side effects of an IUD (intrauterine device) or copper coil - NHS.pdf",                "id": "nhs-iud-sideeff",  "title": "IUD Side Effects",                              "publisher": "NHS", "topic": "contraception", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/contraception/iud-copper-coil/side-effects/"},
    {"file": "Who can get an IUD (intrauterine device) or copper coil - NHS.pdf",                    "id": "nhs-iud-who",      "title": "Who Can Get an IUD?",                           "publisher": "NHS", "topic": "contraception", "doc_type": "patient_education", "url": "https://www.nhs.uk/conditions/contraception/iud-copper-coil/who-can-use-it/"},

    # WHO PDFs
    {"file": "9789240045989-eng.pdf", "id": "who-pdf-045989", "title": "WHO Women's Health Guidelines",      "publisher": "World Health Organization", "topic": "reproductive_health", "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240080591-eng.pdf", "id": "who-pdf-080591", "title": "WHO Reproductive Health Report",     "publisher": "World Health Organization", "topic": "reproductive_health", "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240081727-eng.pdf", "id": "who-pdf-081727", "title": "WHO Maternal Health Brief",          "publisher": "World Health Organization", "topic": "maternal_health",     "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240097490-eng.pdf", "id": "who-pdf-097490", "title": "WHO Global Health Statistics",       "publisher": "World Health Organization", "topic": "reproductive_health", "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240115583-eng.pdf", "id": "who-pdf-115583", "title": "WHO Sexual and Reproductive Health", "publisher": "World Health Organization", "topic": "reproductive_health", "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240115606-eng.pdf", "id": "who-pdf-115606", "title": "WHO Contraception Guidelines",       "publisher": "World Health Organization", "topic": "contraception",       "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240115774-eng.pdf", "id": "who-pdf-115774", "title": "WHO Menstrual Health Policy",        "publisher": "World Health Organization", "topic": "menstrual_health",    "doc_type": "policy_document", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240115835-eng.pdf", "id": "who-pdf-115835", "title": "WHO PCOS Clinical Guidelines",       "publisher": "World Health Organization", "topic": "pcos",                "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
    {"file": "9789240124578-eng.pdf", "id": "who-pdf-124578", "title": "WHO Endometriosis Report",           "publisher": "World Health Organization", "topic": "endometriosis",       "doc_type": "guideline", "url": "https://www.who.int", "min_chars": 2000},
]


def _upsert_registry(session, spec_id: str, title: str, publisher: str, url: str,
                     topic: str, doc_type: str, **fields) -> None:
    from app.db import models
    row = session.get(models.KnowledgeSource, spec_id)
    if row is None:
        row = models.KnowledgeSource(id=spec_id)
        session.add(row)
    row.title = title
    row.publisher = publisher
    row.url = url
    row.doc_type = doc_type
    row.topic = topic
    row.language = "en"
    for key, value in fields.items():
        setattr(row, key, value)
    session.commit()


def ingest(rebuild: bool = False) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()

    embedder = get_embedder()
    store = get_vector_store()
    store.ensure_collection(embedder.dimension, recreate=rebuild)

    today = date.today().isoformat()
    cache_dir = settings.knowledge_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    total_chunks = 0

    with get_sessionmaker()() as session:
        for spec in PDF_MANIFEST:
            pdf_path = DATASET_DIR / spec["file"]
            spec_id = spec["id"]
            if not pdf_path.exists():
                log.warning("[%s] PDF not found at %s — skipping", spec_id, pdf_path)
                failures += 1
                continue

            log.info("[%s] extracting %s", spec_id, spec["file"])
            try:
                extracted = extract_pdf(pdf_path)
                text = extracted.text
                min_chars = spec.get("min_chars", 800)
                if len(text) < min_chars:
                    raise ValueError(f"Only {len(text)} chars extracted (< {min_chars})")

                chunks = chunk_text(text)
                if not chunks:
                    raise ValueError("No chunks produced")

                # Save text snapshot
                snapshot = cache_dir / f"{spec_id}.txt"
                snapshot.write_text(text, encoding="utf-8")
                meta = {
                    "source_id": spec_id,
                    "url": spec["url"],
                    "accessed_date": today,
                    "content_type": "pdf",
                    "extraction_method": extracted.method,
                    "char_count": len(text),
                    "chunk_count": len(chunks),
                    "warnings": extracted.warnings,
                }
                (cache_dir / f"{spec_id}.meta.json").write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
                )

                payloads = [
                    ChunkPayload(
                        chunk_id=f"{spec_id}::{c.index:03d}",
                        source_id=spec_id,
                        title=spec["title"],
                        publisher=spec["publisher"],
                        url=spec["url"],
                        doc_type=spec["doc_type"],
                        topic=spec["topic"],
                        section=c.section,
                        language="en",
                        published_date=None,
                        updated_date=None,
                        accessed_date=today,
                        license_note=None,
                        text=c.text,
                    )
                    for c in chunks
                ]
                vectors = embedder.embed_passages([p.text for p in payloads])
                store.delete_source(spec_id)
                store.upsert(payloads, vectors)

                _upsert_registry(
                    session,
                    spec_id=spec_id,
                    title=spec["title"],
                    publisher=spec["publisher"],
                    url=spec["url"],
                    topic=spec["topic"],
                    doc_type=spec["doc_type"],
                    published_date=None,
                    updated_date=None,
                    accessed_date=today,
                    chunk_count=len(chunks),
                    status="indexed",
                    status_detail=None,
                    ingested_at=datetime.now(timezone.utc),
                )
                total_chunks += len(chunks)
                log.info("[%s] ✓ indexed %d chunks (%d chars)", spec_id, len(chunks), len(text))

            except Exception as exc:  # noqa: BLE001
                failures += 1
                log.error("[%s] FAILED: %s", spec_id, exc)
                try:
                    _upsert_registry(
                        session,
                        spec_id=spec_id,
                        title=spec["title"],
                        publisher=spec["publisher"],
                        url=spec["url"],
                        topic=spec["topic"],
                        doc_type=spec["doc_type"],
                        status="failed",
                        status_detail=str(exc),
                        chunk_count=0,
                    )
                except Exception:
                    pass

    log.info("═" * 60)
    log.info("Ingestion complete — %d total chunks, %d source(s) failed", total_chunks, failures)
    return 1 if failures and failures == len(PDF_MANIFEST) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest local PDFs into SakhiSahay knowledge base")
    parser.add_argument("--rebuild", action="store_true", help="Drop and recreate the vector collection")
    args = parser.parse_args(argv)
    return ingest(rebuild=args.rebuild)


if __name__ == "__main__":
    sys.exit(main())
