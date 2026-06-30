from cidy.reference.sdg import load_sdg_framework

from cidy_api.llm import sdg_suggest

FRAMEWORK = load_sdg_framework(
    {
        "goals": [
            {"goal": 1, "title": "No Poverty", "targets": [{"target": "1.1", "text": "End extreme poverty"}]},
            {"goal": 8, "title": "Decent Work", "targets": [
                {"target": "8.5", "text": "Full and productive employment"},
                {"target": "8.6", "text": "Reduce youth NEET"},
            ]},
        ]
    }
)


class _StubProvider:
    def __init__(self, output: str) -> None:
        self._output = output
        self.last_system = None
        self.last_user = None

    def complete(self, system, user, *, max_tokens=600, temperature=0.3):
        self.last_system = system
        self.last_user = user
        return self._output


def _suggest(output):
    return sdg_suggest.suggest_sdg_targets(
        _StubProvider(output), FRAMEWORK,
        fund="RPTC", artifact_type="activity_proposal", context="jobs for youth",
    )


def test_valid_codes_attached_with_official_title():
    out = _suggest('{"suggestions": [{"target": "8.5", "rationale": "jobs"}]}')
    assert len(out) == 1
    assert out[0].target == "8.5"
    assert out[0].title == "Full and productive employment"  # framework text, not the model's
    assert out[0].rationale == "jobs"


def test_invalid_codes_dropped():
    out = _suggest('{"suggestions": [{"target": "8.5", "rationale": "a"}, {"target": "99.9", "rationale": "b"}]}')
    assert [s.target for s in out] == ["8.5"]


def test_duplicates_dropped():
    out = _suggest('{"suggestions": [{"target": "8.5", "rationale": "a"}, {"target": "8.5", "rationale": "b"}]}')
    assert [s.target for s in out] == ["8.5"]


def test_tolerant_of_code_fences():
    out = _suggest('```json\n{"suggestions": [{"target": "1.1", "rationale": "poverty"}]}\n```')
    assert [s.target for s in out] == ["1.1"]


def test_unparseable_output_returns_empty():
    assert _suggest("sorry, I cannot help") == []


def test_prompt_grounds_on_targets_and_context():
    p = _StubProvider('{"suggestions": []}')
    sdg_suggest.suggest_sdg_targets(
        p, FRAMEWORK, fund="RPTC", artifact_type="activity_proposal", context="youth employment",
    )
    assert "8.5" in p.last_user  # official targets listed
    assert "youth employment" in p.last_user  # project context included
    assert "JSON" in p.last_system
