"""
Export chunks and vector database to a dedicated 'vector_database' folder.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.rag.vector_store import get_vector_store

def export_all():
    target_dir = PROJECT_ROOT / "vector_database"
    chunks_dir = target_dir / "chunks"
    qdrant_dir = target_dir / "qdrant_db"

    chunks_dir.mkdir(parents=True, exist_ok=True)
    qdrant_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory: {target_dir}")

    # 1. Copy Qdrant vector database
    source_qdrant = BACKEND_DIR / "data" / "runtime" / "qdrant"
    if source_qdrant.exists():
        print(f"Copying Qdrant database from {source_qdrant} to {qdrant_dir}...")
        # Remove old contents if any
        for item in qdrant_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        for item in source_qdrant.iterdir():
            dest = qdrant_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest)
        print("Qdrant database files copied successfully!")

    # 2. Extract all chunks from Qdrant
    print("Reading all points from Qdrant vector store...")
    store = get_vector_store()
    
    # Scroll all points
    all_chunks = []
    by_source = {}
    offset = None

    while True:
        points, next_offset = store.client.scroll(
            collection_name=store.collection,
            limit=250,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            break
        for p in points:
            payload = p.payload
            chunk_data = {
                "chunk_id": payload.get("chunk_id"),
                "source_id": payload.get("source_id"),
                "title": payload.get("title"),
                "publisher": payload.get("publisher"),
                "topic": payload.get("topic"),
                "doc_type": payload.get("doc_type"),
                "section": payload.get("section"),
                "url": payload.get("url"),
                "char_count": len(payload.get("text", "")),
                "text": payload.get("text", ""),
            }
            all_chunks.append(chunk_data)
            sid = payload.get("source_id", "unknown")
            if sid not in by_source:
                by_source[sid] = {
                    "source_id": sid,
                    "title": payload.get("title"),
                    "publisher": payload.get("publisher"),
                    "topic": payload.get("topic"),
                    "url": payload.get("url"),
                    "chunks": []
                }
            by_source[sid]["chunks"].append(chunk_data)

        if next_offset is None:
            break
        offset = next_offset

    print(f"Extracted {len(all_chunks)} chunks across {len(by_source)} sources.")

    # 3. Save all_chunks.json
    all_chunks_file = chunks_dir / "all_chunks.json"
    all_chunks_file.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {all_chunks_file} ({len(all_chunks)} chunks, {all_chunks_file.stat().st_size / 1024 / 1024:.2f} MB)")

    # 4. Save manifest & per-source chunk files
    manifest = []
    for sid, data in by_source.items():
        doc_file = chunks_dir / f"{sid}.json"
        doc_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append({
            "source_id": sid,
            "title": data["title"],
            "publisher": data["publisher"],
            "topic": data["topic"],
            "url": data["url"],
            "chunk_count": len(data["chunks"]),
            "file": f"{sid}.json"
        })

    manifest_file = chunks_dir / "chunks_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {manifest_file} with {len(manifest)} source documents.")

    # 5. Create README.md
    readme_file = target_dir / "README.md"
    readme_content = f"""# SakhiSahay Vector Database & Chunks Storage

This directory contains the pre-ingested, embedded clinical knowledge base for the SakhiSahay AI Health Assistant.

---

## Directory Structure

```
vector_database/
├── README.md                  # Documentation and ingestion workflow guide
├── qdrant_db/                 # Persistent local Qdrant Vector Database
│   ├── meta.json              # Qdrant collection schema & index metadata
│   └── collection/            # RocksDB / SQLite vector embeddings & HNSW graphs
└── chunks/                    # Extracted text chunks and metadata
    ├── all_chunks.json        # All {len(all_chunks):,} chunks in a single searchable JSON file
    ├── chunks_manifest.json   # Index of all {len(manifest)} medical sources with chunk counts
    └── *.json                 # Individual per-document chunk files
```

---

## Knowledge Base Statistics

* **Total Clinical Documents**: {len(manifest)} medical reference PDFs
* **Total Embedded Chunks**: {len(all_chunks):,} chunks
* **Vector Embedding Model**: `intfloat/multilingual-e5-small` (384-dimensional dense vectors)
* **Similarity Metric**: Cosine Distance with HNSW indexing
* **Primary Health Authorities**:
  * **ACOG** (American College of Obstetricians and Gynecologists)
  * **NHS** (National Health Service, UK)
  * **CDC** (Centers for Disease Control and Prevention)
  * **WHO** (World Health Organization)

---

## Ingestion & Vector DB Workflow

1. **Raw Document Source**:
   All 37 source clinical publications reside in `dataset/` (PDF format).

2. **Extraction & Chunking** (`Backend/ingest_local.py`):
   * Each PDF is parsed using PyMuPDF (`fitz`).
   * Clean text is split using semantic sliding-window chunking (target size ~500-800 characters) preserving headings and bulleted clinical lists.
   * Chunks are saved to `vector_database/chunks/`.

3. **Vector Embedding**:
   * Text passages are prefixed with `passage: ` and embedded with `intfloat/multilingual-e5-small`.
   * High-dimensional embeddings (384-d vectors) are indexed directly into the local Qdrant instance in `vector_database/qdrant_db/`.

4. **Re-ingesting or Updating Knowledge**:
   To re-ingest all files from `dataset/` and rebuild the vector database:
   ```powershell
   cd Backend
   python ingest_local.py --rebuild
   ```

5. **Runtime Querying**:
   When a user asks a question in the chatbot:
   * Query is embedded with `query: <user text>`.
   * Cosine similarity search against `qdrant_db/` retrieves top clinical chunks.
   * Evidence is formatted into an LLM prompt for citation synthesis.
"""
    readme_file.write_text(readme_content, encoding="utf-8")
    print(f"Created {readme_file}")

if __name__ == "__main__":
    export_all()
