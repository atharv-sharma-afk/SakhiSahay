"""Sentence-embedding wrapper.

E5-family models are trained with "query: " / "passage: " prefixes; omitting
them measurably degrades retrieval, so the wrapper applies them automatically
when the configured model id looks like an E5 model.
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger("sakhisahay.embeddings")


class Embedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._is_e5 = "e5" in model_name.lower()
        log.info("loading embedding model %s", model_name)
        self._model = SentenceTransformer(model_name, device="cpu")
        self.dimension = int(self._model.get_sentence_embedding_dimension())
        self._lock = threading.Lock()

    def _encode(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            vectors = self._model.encode(texts, batch_size=16, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts] if self._is_e5 else texts
        return self._encode(prefixed)

    def embed_query(self, text: str) -> list[float]:
        prefixed = f"query: {text}" if self._is_e5 else text
        return self._encode([prefixed])[0]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder(get_settings().embedding_model)
