from cidy.artifact.models import Artifact
from cidy.artifact.validation import ValidationReport, validate_artifact
from cidy.reference.sdg import load_sdg_framework
from cidy.schema.models import (
    Constraints,
    Field,
    FieldType,
    Section,
    TemplateSchema,
)

FW = load_sdg_framework(
    {"goals": [{"goal": 8, "title": "Decent Work", "targets": [{"target": "8.5", "text": "..."}]}]}
)

SCHEMA = TemplateSchema(
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
                Field(id="objective", label="Objective", type=FieldType.RICH_TEXT,
                      constraints=Constraints(required=True, max_words=3)),
                Field(id="sdgs", label="SDGs", type=FieldType.SDG_TARGET_LIST,
                      constraints=Constraints(max_items=10, order="ascending")),
            ],
        ),
        Section(
            id="outcomes",
            title="Outcomes",
            repeating=True,
            fields=[Field(id="outcome", label="Outcome", type=FieldType.TEXT,
                          constraints=Constraints(required=True))],
        ),
    ],
)


def test_valid_artifact_passes():
    art = Artifact(
        schema_id="demo", schema_version="1",
        values={
            "background": {"objective": "Improve health", "sdgs": ["8.5"]},
            "outcomes": [{"outcome": "OC1"}],
        },
    )
    report = validate_artifact(SCHEMA, art, FW)
    assert isinstance(report, ValidationReport)
    assert report.is_valid is True
    assert report.required_total == 2  # objective + one repeating outcome
    assert report.required_filled == 2


def test_missing_required_reported():
    art = Artifact(schema_id="demo", schema_version="1",
                   values={"background": {"sdgs": ["8.5"]}, "outcomes": []})
    report = validate_artifact(SCHEMA, art, FW)
    assert report.is_valid is False
    assert "background.objective" in report.missing


def test_field_constraint_violation_reported():
    art = Artifact(schema_id="demo", schema_version="1",
                   values={"background": {"objective": "one two three four", "sdgs": []},
                           "outcomes": [{"outcome": "OC1"}]})
    report = validate_artifact(SCHEMA, art, FW)
    assert any("words" in i.message and i.path == "background.objective" for i in report.issues)


def test_repeating_item_paths():
    art = Artifact(schema_id="demo", schema_version="1",
                   values={"background": {"objective": "ok", "sdgs": []},
                           "outcomes": [{"outcome": "OC1"}, {"outcome": ""}]})
    report = validate_artifact(SCHEMA, art, FW)
    assert "outcomes[1].outcome" in report.missing
