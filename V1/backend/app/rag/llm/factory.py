from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.rag.llm.base import LLMProvider


@lru_cache
def get_llm() -> LLMProvider | None:
    """Return the configured provider, or None when generation is disabled/unconfigured."""
    settings = get_settings()
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        from app.rag.llm.gemini import GeminiProvider

        return GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds)
    return None
