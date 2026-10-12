from __future__ import annotations

import logging
import time

from app.rag.llm.base import LLMResult, LLMUnavailable

log = logging.getLogger("sakhisahay.llm.gemini")

_MAX_RETRIES = 2
_RETRY_DELAYS = [1.5, 3.0]  # seconds between retries


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        self.model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    def generate(self, system: str, user: str) -> LLMResult:
        from google.genai import errors
        from app.config import get_settings

        types = self._types
        settings = get_settings()
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=settings.gemini_temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
            safety_settings=[
                # Women's health questions legitimately mention anatomy and sexual health;
                # the default thresholds over-block them. Keep blocking on genuinely harmful content.
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )

        last_exc: LLMUnavailable | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(model=self.model, contents=user, config=config)
                break  # success
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                message = str(exc)
                # Non-retryable: auth failures
                if code in (401, 403) or "API key" in message or "API_KEY_INVALID" in message:
                    raise LLMUnavailable("The language-model API key was rejected. Check GEMINI_API_KEY.") from exc
                # Retryable: rate limit and server errors
                retryable = (code == 429) or (code is not None and code >= 500)
                if retryable and attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAYS[attempt]
                    log.warning("gemini api error code=%s attempt=%d, retrying in %.1fs", code, attempt + 1, delay)
                    time.sleep(delay)
                    last_exc = LLMUnavailable("The language-model service is temporarily unavailable.", retryable=True)
                    continue
                if code == 429:
                    raise LLMUnavailable("The language model is rate-limited right now. Please retry shortly.", retryable=True) from exc
                if code is not None and code >= 500:
                    raise LLMUnavailable("The language-model service is temporarily unavailable.", retryable=True) from exc
                log.warning("gemini api error code=%s", code)
                raise LLMUnavailable("The language model could not process this request.") from exc
            except Exception as exc:  # timeouts, network, SDK errors
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAYS[attempt]
                    log.warning("gemini call failed: %s attempt=%d, retrying in %.1fs", type(exc).__name__, attempt + 1, delay)
                    time.sleep(delay)
                    last_exc = LLMUnavailable("Could not reach the language model (timeout or network error).", retryable=True)
                    continue
                log.warning("gemini call failed after %d retries: %s", _MAX_RETRIES, type(exc).__name__)
                raise LLMUnavailable("Could not reach the language model (timeout or network error).", retryable=True) from exc
        else:
            # All retries exhausted
            raise (last_exc or LLMUnavailable("The language-model service is temporarily unavailable.", retryable=True))

        text = (response.text or "").strip() if hasattr(response, "text") else ""
        if not text:
            finish = None
            try:
                finish = response.candidates[0].finish_reason  # type: ignore[index]
            except Exception:
                pass
            raise LLMUnavailable(f"The language model returned no answer (finish_reason={finish}).")

        usage = getattr(response, "usage_metadata", None)
        return LLMResult(
            text=text,
            model=self.model,
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )

