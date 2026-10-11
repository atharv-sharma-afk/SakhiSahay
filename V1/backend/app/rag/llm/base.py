from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMUnavailable(RuntimeError):
    """Raised for any provider failure; the message is safe to show to users."""

    def __init__(self, reason: str, retryable: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.retryable = retryable


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, system: str, user: str) -> LLMResult: ...
