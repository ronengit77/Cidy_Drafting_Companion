from cidy.artifact.sdg_validator import validate_sdg_target_list
from cidy.reference.sdg import load_sdg_framework
from cidy.schema.models import Constraints

FW = load_sdg_framework(
    {
        "goals": [
            {"goal": 1, "title": "No Poverty", "targets": [{"target": "1.2", "text": "..."}]},
            {
                "goal": 8,
                "title": "Decent Work",
                "targets": [
                    {"target": "8.5", "text": "..."},
                    {"target": "8.6", "text": "..."},
                ],
            },
        ]
    }
)


def test_valid_ascending_within_max():
    c = Constraints(max_items=10, order="ascending")
    assert validate_sdg_target_list(["1.2", "8.5", "8.6"], c, FW, "s.f") == []


def test_unknown_target_flagged():
    issues = validate_sdg_target_list(["9.9"], Constraints(), FW, "s.f")
    assert issues[0].severity == "error"
    assert "9.9" in issues[0].message


def test_too_many_items():
    c = Constraints(max_items=2)
    issues = validate_sdg_target_list(["1.2", "8.5", "8.6"], c, FW, "s.f")
    assert any("at most 2" in i.message for i in issues)


def test_not_ascending_flagged():
    c = Constraints(order="ascending")
    issues = validate_sdg_target_list(["8.6", "8.5"], c, FW, "s.f")
    assert any("ascending" in i.message for i in issues)


def test_none_is_ok():
    assert validate_sdg_target_list(None, Constraints(), FW, "s.f") == []


def test_lettered_targets_sorted_after_numeric_ascending():
    fw = load_sdg_framework(
        {
            "goals": [
                {"goal": 1, "title": "No Poverty", "targets": [
                    {"target": "1.1", "text": "..."},
                    {"target": "1.a", "text": "..."},
                ]},
                {"goal": 8, "title": "Decent Work", "targets": [
                    {"target": "8.5", "text": "..."},
                    {"target": "8.a", "text": "..."},
                ]},
            ]
        }
    )
    c = Constraints(order="ascending")
    # numeric-before-lettered within a goal, goals ascending -> valid, no crash
    assert validate_sdg_target_list(["1.1", "1.a", "8.5", "8.a"], c, fw, "s.f") == []
    # lettered before its own numeric sibling -> not ascending
    issues = validate_sdg_target_list(["1.a", "1.1"], c, fw, "s.f")
    assert any("ascending" in i.message for i in issues)
