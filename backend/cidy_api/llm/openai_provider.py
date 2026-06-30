from __future__ import annotations

from typing import Any

from cidy_api.llm.base import LLMError


class OpenAIProvider:
    def __init__(self, *, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)

    def complete(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3
    ) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001 - normalize all provider errors
            raise LLMError(str(exc)) from exc
