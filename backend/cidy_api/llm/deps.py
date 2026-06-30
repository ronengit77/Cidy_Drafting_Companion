from __future__ import annotations

from cidy_api.config import get_settings
from cidy_api.llm.base import LLMProvider
from cidy_api.llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIProvider(api_key=settings.openai_api_key, model=settings.llm_model)
