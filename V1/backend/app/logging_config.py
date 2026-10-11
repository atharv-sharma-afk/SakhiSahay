from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Structured-enough console logging.

    Handlers deliberately never receive message bodies, symptom notes, or
    retrieved health text; call sites log counts, ids, and timings only.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
