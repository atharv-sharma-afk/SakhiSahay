from __future__ import annotations

import logging

from app.rag.llm.base import LLMResult, LLMUnavailable

log = logging.getLogger("sakhisahay.llm.gemini")


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

        types = self._types
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=1400,
            safety_settings=[
                # Women's health questions legitimately mention anatomy and sexual health;
                # the default thresholds over-block them. Keep blocking on genuinely harmful content.
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )
        try:
            response = self._client.models.generate_content(model=self.model, contents=user, config=config)
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            message = str(exc)
            # Gemini reports an invalid key as 400 INVALID_ARGUMENT ("API key not valid"), not 401.
            if code in (401, 403) or "API key" in message or "API_KEY_INVALID" in message:
                raise LLMUnavailable("The language-model API key was rejected. Check GEMINI_API_KEY.") from exc
            if code == 429:
                raise LLMUnavailable("The language model is rate-limited right now. Please retry shortly.", retryable=True) from exc
            if code and code >= 500:
                raise LLMUnavailable("The language-model service is temporarily unavailable.", retryable=True) from exc
            log.warning("gemini api error code=%s", code)
            raise LLMUnavailable("The language model could not process this request.") from exc
        except Exception as exc:  # timeouts, network, SDK errors
            log.warning("gemini call failed: %s", type(exc).__name__)
            raise LLMUnavailable("Could not reach the language model (timeout or network error).", retryable=True) from exc

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
