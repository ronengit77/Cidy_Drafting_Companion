from __future__ import annotations


class EchoLLMProvider:
    """Deterministic provider for tests: echoes the user prompt, records inputs."""

    def __init__(self) -> None:
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3
    ) -> str:
        self.last_system = system
        self.last_user = user
        return user
