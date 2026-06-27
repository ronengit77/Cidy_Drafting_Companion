from cidy.artifact.field_validators import Issue, validate_field_value
from cidy.schema.models import Constraints, Field, FieldType


def _field(type_, **constraints):
    return Field(id="f", label="F", type=type_, constraints=Constraints(**constraints))


def test_text_within_limits_ok():
    assert validate_field_value(_field(FieldType.TEXT, max_words=3), "one two", "s.f") == []


def test_text_exceeds_max_words():
    issues = validate_field_value(_field(FieldType.TEXT, max_words=2), "one two three", "s.f")
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "words" in issues[0].message
    assert issues[0].path == "s.f"


def test_text_exceeds_max_chars():
    issues = validate_field_value(_field(FieldType.TEXT, max_chars=3), "abcd", "s.f")
    assert issues[0].severity == "error"
    assert "characters" in issues[0].message


def test_number_must_be_numeric():
    issues = validate_field_value(_field(FieldType.NUMBER), "not a number", "s.f")
    assert issues[0].severity == "error"


def test_currency_non_negative():
    issues = validate_field_value(_field(FieldType.CURRENCY, min_value=0), -5, "s.f")
    assert issues[0].severity == "error"


def test_boolean_accepts_bool():
    assert validate_field_value(_field(FieldType.BOOLEAN), True, "s.f") == []


def test_boolean_rejects_non_bool():
    issues = validate_field_value(_field(FieldType.BOOLEAN), "yes", "s.f")
    assert issues[0].severity == "error"


def test_single_select_must_be_in_options():
    f = _field(FieldType.SINGLE_SELECT, options=["a", "b"])
    assert validate_field_value(f, "a", "s.f") == []
    assert validate_field_value(f, "c", "s.f")[0].severity == "error"


def test_multi_select_all_in_options():
    f = _field(FieldType.MULTI_SELECT, options=["a", "b", "c"])
    assert validate_field_value(f, ["a", "c"], "s.f") == []
    assert validate_field_value(f, ["a", "z"], "s.f")[0].severity == "error"


def test_none_value_yields_no_field_issue():
    assert validate_field_value(_field(FieldType.TEXT, max_words=2), None, "s.f") == []
