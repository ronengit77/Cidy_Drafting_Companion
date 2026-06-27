import pytest
from pydantic import ValidationError

from cidy.schema.models import (
    Constraints,
    Field,
    FieldType,
    Section,
    TemplateSchema,
)


def test_build_minimal_schema():
    schema = TemplateSchema(
        schema_id="demo",
        version="1",
        fund="DA",
        artifact_type="concept_note",
        title="Demo",
        sections=[
            Section(
                id="background",
                title="Background",
                fields=[
                    Field(
                        id="objective",
                        label="Objective",
                        type=FieldType.RICH_TEXT,
                        constraints=Constraints(required=True, max_words=200),
                    )
                ],
            )
        ],
    )
    assert schema.sections[0].fields[0].type is FieldType.RICH_TEXT
    assert schema.sections[0].fields[0].constraints.required is True


def test_repeating_group_field_has_nested_fields():
    field = Field(
        id="outputs",
        label="Outputs",
        type=FieldType.REPEATING_GROUP,
        fields=[Field(id="output", label="Output", type=FieldType.RICH_TEXT)],
    )
    assert field.fields[0].id == "output"


def test_unknown_field_type_rejected():
    with pytest.raises(ValidationError):
        Field(id="x", label="X", type="not_a_type")
