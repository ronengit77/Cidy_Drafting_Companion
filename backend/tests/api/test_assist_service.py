from cidy.schema.models import Field, FieldType, Section, TemplateSchema

from cidy_api.llm import assist
from cidy_api.llm.fake import EchoLLMProvider


def _schema() -> TemplateSchema:
    return TemplateSchema(
        schema_id="demo", version="1", fund="RPTC", artifact_type="activity_proposal",
        title="Demo",
        sections=[
            Section(id="cover", title="Cover", fields=[
                Field(id="brief", label="Brief description", type=FieldType.RICH_TEXT,
                      guidance="300 words max; be specific."),
            ]),
            Section(id="caps", title="Capacities", repeating=True, fields=[
                Field(id="capacity", label="Capacity", type=FieldType.RICH_TEXT),
            ]),
        ],
    )


def test_shape_field_grounds_prompt_and_returns_text():
    p = EchoLLMProvider()
    out = assist.shape_field(
        p, fund="RPTC", artifact_type="activity_proposal", section_title="Cover",
        field_label="Brief description", field_guidance="300 words max; be specific.",
        raw_input="we will train tax officials",
    )
    assert out == "we will train tax officials"  # echo returns the user text
    assert "Brief description" in p.last_system
    assert "300 words max" in p.last_system
    assert "RPTC" in p.last_system


def test_render_artifact_summary_includes_values_and_repeats():
    schema = _schema()
    values = {
        "cover": {"brief": "Strengthen capacity"},
        "caps": [{"capacity": "Increased knowledge"}, {"capacity": "Better tools"}],
    }
    summary = assist.render_artifact_summary(schema, values)
    assert "Cover / Brief description: Strengthen capacity" in summary
    assert "Capacities [1] / Capacity: Increased knowledge" in summary
    assert "Capacities [2] / Capacity: Better tools" in summary


def test_coherence_check_reviews_summary():
    p = EchoLLMProvider()
    schema = _schema()
    out = assist.coherence_check(p, schema=schema, values={"cover": {"brief": "X"}})
    assert isinstance(out, str) and out
    assert "coherence" in p.last_system.lower()
    assert "Brief description: X" in p.last_user
