#!/usr/bin/env python3
"""
SakhiSahay — one-click setup and startup script.

Run this from the Backend/ directory:
    python start.py

What it does:
  1. Checks GEMINI_API_KEY in .env
  2. Checks if the vector DB has been indexed; if not, runs ingest_local.py
  3. Starts the FastAPI server on port 8000
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"


def check_and_prompt_api_key() -> bool:
    """Return True if GEMINI_API_KEY is set in .env."""
    if not ENV_FILE.exists():
        print("❌  .env file not found. Creating a template...")
        ENV_FILE.write_text(
            "GEMINI_API_KEY=PASTE_YOUR_KEY_HERE\n"
            "GEMINI_MODEL=gemini-2.0-flash\n"
            "EMBEDDING_MODEL=intfloat/multilingual-e5-small\n"
            "QDRANT_PATH=./data/runtime/qdrant\n"
            "DATABASE_URL=sqlite:///./data/runtime/sakhisahay.db\n"
            "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n"
            "AUTH_MODE=local\n"
            "LOG_LEVEL=INFO\n",
            encoding="utf-8",
        )

    content = ENV_FILE.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("GEMINI_API_KEY="):
            val = line.split("=", 1)[1].strip()
            if val and val != "PASTE_YOUR_KEY_HERE" and not val.startswith("#"):
                return True

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    🔑  API KEY REQUIRED                      ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                                                              ║")
    print("║  SakhiSahay needs a Google Gemini API key to generate        ║")
    print("║  AI-powered health answers.                                  ║")
    print("║                                                              ║")
    print("║  Get a FREE key (takes 30 seconds):                          ║")
    print("║  👉  https://aistudio.google.com/app/apikey                  ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    key = input("Paste your Gemini API key here (or press Enter to skip): ").strip()
    if key:
        # Write key into .env
        lines = content.splitlines()
        new_lines = []
        replaced = False
        for ln in lines:
            if ln.strip().startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={key}")
                replaced = True
            else:
                new_lines.append(ln)
        if not replaced:
            new_lines.append(f"GEMINI_API_KEY={key}")
        ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        print("✅  API key saved to Backend/.env")
        return True
    else:
        print("⚠️   Skipping API key — the chatbot will run in retrieval-only mode (no AI generation).")
        return False


def check_index_ready() -> bool:
    """Check if the Qdrant index has at least one chunk."""
    try:
        sys.path.insert(0, str(BACKEND_DIR))
        from app.rag.pipeline import get_pipeline_status
        status = get_pipeline_status()
        return status.get("index_ready", False) and status.get("chunk_count", 0) > 0
    except Exception as exc:
        print(f"⚠️   Could not check index: {exc}")
        return False


def run_ingestion() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          📚  BUILDING KNOWLEDGE BASE (first run)             ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  Extracting text from 37 medical PDFs and building the       ║")
    print("║  vector index. This takes 5–15 minutes on first run.         ║")
    print("║  Subsequent startups are instant (the index is cached).      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    result = subprocess.run(
        [sys.executable, "ingest_local.py"],
        cwd=BACKEND_DIR,
    )
    if result.returncode != 0:
        print("❌  Ingestion failed. Check the logs above for details.")
        print("    The server will start but will answer in retrieval-only mode.")
    else:
        print("✅  Knowledge base ready!")


def start_server() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           🌸  STARTING SAKHISAHAY BACKEND API               ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  API:      http://localhost:8000                             ║")
    print("║  Docs:     http://localhost:8000/docs                        ║")
    print("║  Frontend: http://localhost:3000  (run 'node server.js')     ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=BACKEND_DIR,
    )


def main() -> None:
    print()
    print("  🌸  SakhiSahay Backend Setup & Launch")
    print("  " + "─" * 46)
    print()

    # Step 1: API key
    check_and_prompt_api_key()

    # Step 2: Vector index
    print("🔍  Checking knowledge base index...")
    if not check_index_ready():
        run_ingestion()
    else:
        print("✅  Knowledge base already indexed — skipping ingestion.")

    # Step 3: Start API
    start_server()


if __name__ == "__main__":
    main()
