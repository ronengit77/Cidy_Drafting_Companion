from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Raised when an LLM provider call fails."""


@runtime_checkable
class LLMProvider(Protocol):
    def complete(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3
    ) -> str: ...
