import os
from unittest.mock import MagicMock

import pytest

from cidy_api.llm.base import LLMError
from cidy_api.llm.openai_provider import OpenAIProvider


def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )
    return client


def test_complete_builds_request_and_returns_content():
    client = _mock_client("shaped result")
    p = OpenAIProvider(api_key="x", model="gpt-4o-mini", client=client)
    out = p.complete("sys", "usr", max_tokens=123, temperature=0.1)
    assert out == "shaped result"
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["max_tokens"] == 123
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][1] == {"role": "user", "content": "usr"}


def test_complete_wraps_errors_in_llm_error():
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("boom")
    p = OpenAIProvider(api_key="x", model="m", client=client)
    with pytest.raises(LLMError):
        p.complete("s", "u")


@pytest.mark.skipif(os.getenv("CIDY_LLM_LIVE_TESTS") != "1", reason="live LLM test disabled")
def test_openai_live_smoke():
    from cidy_api.config import get_settings

    s = get_settings()
    if not s.openai_api_key:
        pytest.skip("no OPENAI_API_KEY configured")
    p = OpenAIProvider(api_key=s.openai_api_key, model=s.llm_model)
    out = p.complete("Reply with exactly the word OK.", "Are you there?")
    assert isinstance(out, str) and out.strip()
