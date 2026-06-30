from cidy_api.llm.base import LLMProvider
from cidy_api.llm.fake import EchoLLMProvider


def test_echo_provider_satisfies_protocol_and_records():
    p = EchoLLMProvider()
    assert isinstance(p, LLMProvider)
    out = p.complete("system text", "user text", max_tokens=10)
    assert out == "user text"
    assert p.last_system == "system text"
    assert p.last_user == "user text"


def test_llm_settings_defaults_and_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    from cidy_api.config import Settings

    s = Settings()
    assert s.llm_model == "gpt-4o-mini"
    assert s.openai_api_key == "sk-test-123"
