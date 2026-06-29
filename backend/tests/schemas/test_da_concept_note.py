from pathlib import Path

from cidy.schema.loader import load_schema_file

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "da-concept-note.v19.json"


def test_da_schema_loads():
    schema = load_schema_file(SCHEMA_PATH)
    assert schema.fund == "DA"
    assert schema.artifact_type == "concept_note"


def test_da_required_sections_present():
    schema = load_schema_file(SCHEMA_PATH)
    ids = {s.id for s in schema.sections}
    required = {
        "background",
        "fascicle_data",
        "outcomes_outputs",
        "un_coordination",
        "partnerships",
        "budget_narrative",
    }
    assert required.issubset(ids)


def test_background_has_sdg_target_list_max_10_ascending():
    schema = load_schema_file(SCHEMA_PATH)
    background = next(s for s in schema.sections if s.id == "background")
    sdg = next(f for f in background.fields if f.type.value == "sdg_target_list")
    assert sdg.constraints.max_items == 10
    assert sdg.constraints.order == "ascending"
