# SakhiSahay Vector Database & Chunks Storage

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
    ├── all_chunks.json        # All 3,789 chunks in a single searchable JSON file
    ├── chunks_manifest.json   # Index of all 37 medical sources with chunk counts
    └── *.json                 # Individual per-document chunk files
```

---

## Knowledge Base Statistics

* **Total Clinical Documents**: 37 medical reference PDFs
* **Total Embedded Chunks**: 3,789 chunks
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
