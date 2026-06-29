from pathlib import Path

from cidy.schema.loader import load_schema_file

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "schemas" / "rptc-activity-proposal.v2024.json"
)


def test_rptc_schema_loads():
    schema = load_schema_file(SCHEMA_PATH)
    assert schema.fund == "RPTC"
    assert schema.artifact_type == "activity_proposal"


def test_rptc_required_sections_present():
    schema = load_schema_file(SCHEMA_PATH)
    ids = {s.id for s in schema.sections}
    required = {
        "cover_sheet",
        "problem_analysis",
        "desa_mandate",
        "sdgs",
        "target_group",
        "capacities",
        "activities",
        "coherence",
        "inclusion",
        "inputs",
        "financials",
    }
    assert required.issubset(ids)


def test_brief_description_word_limit():
    schema = load_schema_file(SCHEMA_PATH)
    cover = next(s for s in schema.sections if s.id == "cover_sheet")
    brief = next(f for f in cover.fields if f.id == "brief_description")
    assert brief.constraints.max_words == 300
