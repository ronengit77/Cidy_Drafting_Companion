"""Integration tests: authored schemas validate cleanly against the real SDG framework.

These guard the Phase 1 core deliverable -- that the DA Concept Note and RPTC
Activity Proposal schemas, as authored, can be fully and validly filled in and
that the validation engine correctly flags a single missing required field.

For each schema we build one fully-populated, valid `Artifact` covering every
required field, every required repeating section (with at least one item), and
every required nested `repeating_group` sub-field (with at least one populated
item). We then assert the engine reports it valid with nothing missing. A
second test removes exactly one required field from that same baseline and
asserts the engine catches it.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from cidy.artifact.models import Artifact
from cidy.artifact.validation import validate_artifact
from cidy.reference.sdg import load_sdg_framework_file
from cidy.schema.loader import load_schema_file

ROOT = Path(__file__).resolve().parents[3]
DA_SCHEMA_PATH = ROOT / "schemas" / "da-concept-note.v19.json"
RPTC_SCHEMA_PATH = ROOT / "schemas" / "rptc-activity-proposal.v2024.json"
SDG_FRAMEWORK_PATH = ROOT / "data" / "sdg_framework.json"

# Valid, ascending SDG target codes (real codes from data/sdg_framework.json).
VALID_SDG_TARGETS = ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3"]


@pytest.fixture(scope="module")
def da_schema():
    return load_schema_file(DA_SCHEMA_PATH)


@pytest.fixture(scope="module")
def rptc_schema():
    return load_schema_file(RPTC_SCHEMA_PATH)


@pytest.fixture(scope="module")
def sdg_framework():
    return load_sdg_framework_file(SDG_FRAMEWORK_PATH)


def build_valid_da_artifact(schema) -> Artifact:
    """A fully-populated, valid DA Concept Note artifact.

    Fills every required field in `background`, gives the required
    `outcomes_outputs` repeating section one item (with its required
    top-level `outcome` and its required nested `outputs[].output`), and
    gives `budget_narrative.consultants_105` one item satisfying its
    required nested `consultant_category`.
    """
    return Artifact(
        schema_id=schema.schema_id,
        schema_version=schema.version,
        title="Capacity building on international tax cooperation",
        values={
            "background": {
                "fascicle_title": "Strengthening international tax cooperation",
                "implementing_entity": "UN DESA",
                "joint_entities": "",
                "collaborating_entities": "",
                "total_budget": 250,
                "sdg_targets": VALID_SDG_TARGETS,
                "objective": "Strengthen the capacity of developing countries to "
                "participate in international tax cooperation.",
                "project_plan": "The project will deliver training, advisory "
                "support, and knowledge products over 24 months.",
                "expected_progress": "Increased institutional capacity to "
                "negotiate and administer cross-border tax rules.",
                "budget_summary": {
                    "other_staff_costs": 10,
                    "consultants": 50,
                    "travel_of_staff": 20,
                    "contractual_services": 5,
                    "general_operating_expenses": 5,
                    "grants_and_contributions": 10,
                    "total": 100,
                },
            },
            "fascicle_data": {
                "sids": True,
                "lldc": False,
                "ldc": True,
                "regions": ["Africa", "Asia and the Pacific"],
                "sdgs_contributed": ["8", "17"],
                "partnership_types": ["Development Account entities"],
                "consultancy_requirements": {"international": 2, "national": 4},
                "deliverables_seminars_workshops": 5,
                "deliverables_technical_materials": 3,
                "deliverables_consultation_advice": True,
                "deliverables_databases": False,
            },
            "outcomes_outputs": [
                {
                    "outcome": "Improved capacity to negotiate cross-border tax rules.",
                    "outputs": [
                        {"output": "Training delivered to tax officials."},
                    ],
                },
            ],
            "un_coordination": {
                "rco_country": "Kenya",
                "rco_involvement": "RCO will help identify participating ministries.",
            },
            "partnerships": {
                "partnerships_text": "Partnership with regional tax administration forums.",
            },
            "budget_narrative": {
                "gta_015": "Temporary assistance supporting OP1.1.",
                "consultants_105": [
                    {
                        "consultant_category": "International",
                        "consultant_task_description": "Lead trainer for OP1.1.",
                        "consultant_work_months": 3,
                        "consultant_cost": 30000,
                    },
                ],
                "travel_115": [
                    {
                        "travel_staff_category": "Lead entity staff",
                        "travel_purpose": "Mission to support OP1.1.",
                        "travel_num_missions": 2,
                        "travel_cost": 8000,
                    },
                ],
                "contractual_120": "Contracted services for materials development.",
                "goe_125": "General operating expenses for workshops.",
                "grants_145": [
                    {
                        "grant_activity_type": "Workshop / Seminar / Expert Group Meeting",
                        "grant_activity_description": "Regional workshop on tax cooperation.",
                        "grant_cost": 15000,
                    },
                ],
            },
        },
    )


def build_valid_rptc_artifact(schema) -> Artifact:
    """A fully-populated, valid RPTC Activity Proposal artifact.

    Fills every required field in `cover_sheet`, `problem_analysis`,
    `target_group`, and `financials`; gives the required repeating sections
    `desa_mandate`, `capacities`, and `activities` one item each with their
    required fields filled; and sets a valid `sdgs.sdg_targets` list.
    """
    return Artifact(
        schema_id=schema.schema_id,
        schema_version=schema.version,
        title="Capacity building on tax cooperation",
        values={
            "cover_sheet": {
                "project_id": "SB-24-001",
                "implementing_division": "Financing for Sustainable Development Office",
                "branch_name": "Tax Cooperation Branch",
                "title_of_activity": "Strengthening international tax cooperation",
                "brief_description": "Strengthen developing-country capacity in "
                "international tax cooperation through training and advisory support.",
                "proposed_budget": 75000,
                "planned_start_quarter": "2026-Q1",
                "planned_end_quarter": "2026-Q4",
                "focal_point_name": "Jane Doe",
                "focal_point_email": "jane.doe@un.org",
                "level_of_intervention": "Regional",
                # `countries` constraints.options is an empty list in the
                # authored schema (no enumerated country list yet), so any
                # non-empty selection would fail the multi_select "must be
                # one of []" check. Leave unset until the schema defines a
                # country list.
                "nature_of_demand": "Request",
                "meeting_type": "In person",
                "venue_location": "Nairobi, Kenya",
                "division_director_signoff": "",
                "cdpmo_head_signoff": "",
            },
            "problem_analysis": {
                "problem_analysis": "Limited institutional capacity to negotiate "
                "and administer cross-border tax rules.",
            },
            "desa_mandate": [
                {
                    "mandate": "ECOSOC resolution on international tax cooperation.",
                    "contribution": "This activity directly supports the mandate "
                    "by delivering targeted capacity-building support.",
                },
            ],
            "additional_mandate_info": {
                "additional_info": "",
            },
            "recipient_country_request": {
                "recipient_country_request": "Requested by the Ministry of Finance of Kenya.",
            },
            "sdgs": {
                "sdg_targets": ["17.1", "8.5"],
                "themes": ["Financing for Sustainable Development"],
                "sub_themes": "Domestic resource mobilization.",
                "additional_themes": "",
            },
            "target_group": {
                "target_group": "Mid-level officials in national tax administrations.",
            },
            "capacities": [
                {
                    "capacity": "Ability to apply international tax standards.",
                    "indicator": "Number of officials trained.",
                },
            ],
            "activities": [
                {
                    "activity_title": "Regional training workshop on tax cooperation",
                    "activity_planned_start_quarter": "2026-Q2",
                    "activity_planned_end_quarter": "2026-Q2",
                },
            ],
            "coherence": {
                "coherence": "Builds on prior Development Account capacity-building work.",
            },
            "inclusion": {
                "narrative": "Participant selection will target gender balance.",
                "gender_rating": "1",
                "disability_rating": "0",
            },
            "inputs": {
                "desa_inkind": "Staff time for coordination.",
                "desa_cash": "",
                "desa_comments": "",
                "recipient_inkind": "Venue and logistics support.",
                "recipient_cash": "",
                "recipient_comments": "",
                "other_inkind": "",
                "other_cash": "",
                "other_comments": "",
            },
            "financials": {
                "staff_travel": 8000,
                "participants_travel": 20000,
                "consultants": 30000,
                "conference_services": 9000,
                "total": 67000,
                "supplementary_funding": "",
            },
        },
    )


# ---------------------------------------------------------------------------
# DA Concept Note
# ---------------------------------------------------------------------------


def test_da_concept_note_fully_populated_artifact_is_valid(da_schema, sdg_framework):
    artifact = build_valid_da_artifact(da_schema)

    report = validate_artifact(da_schema, artifact, sdg_framework)

    assert report.missing == []
    assert report.is_valid is True


@pytest.mark.parametrize(
    "remove_path",
    [
        "background.fascicle_title",
        "background.implementing_entity",
        "background.objective",
        "background.project_plan",
        "background.expected_progress",
        "background.budget_summary",
        "outcomes_outputs[0].outcome",
        "outcomes_outputs[0].outputs[0].output",
        "budget_narrative.consultants_105[0].consultant_category",
    ],
)
def test_da_concept_note_missing_required_field_is_caught(da_schema, sdg_framework, remove_path):
    artifact = build_valid_da_artifact(da_schema)
    values = copy.deepcopy(artifact.values)

    if remove_path == "background.fascicle_title":
        del values["background"]["fascicle_title"]
    elif remove_path == "background.implementing_entity":
        del values["background"]["implementing_entity"]
    elif remove_path == "background.objective":
        del values["background"]["objective"]
    elif remove_path == "background.project_plan":
        del values["background"]["project_plan"]
    elif remove_path == "background.expected_progress":
        del values["background"]["expected_progress"]
    elif remove_path == "background.budget_summary":
        del values["background"]["budget_summary"]
    elif remove_path == "outcomes_outputs[0].outcome":
        del values["outcomes_outputs"][0]["outcome"]
    elif remove_path == "outcomes_outputs[0].outputs[0].output":
        del values["outcomes_outputs"][0]["outputs"][0]["output"]
    elif remove_path == "budget_narrative.consultants_105[0].consultant_category":
        del values["budget_narrative"]["consultants_105"][0]["consultant_category"]
    else:
        raise AssertionError(f"unhandled remove_path: {remove_path}")

    artifact.values = values
    report = validate_artifact(da_schema, artifact, sdg_framework)

    assert report.is_valid is False
    assert remove_path in report.missing


# ---------------------------------------------------------------------------
# RPTC Activity Proposal
# ---------------------------------------------------------------------------


def test_rptc_activity_proposal_fully_populated_artifact_is_valid(rptc_schema, sdg_framework):
    artifact = build_valid_rptc_artifact(rptc_schema)

    report = validate_artifact(rptc_schema, artifact, sdg_framework)

    assert report.missing == []
    assert report.is_valid is True


@pytest.mark.parametrize(
    "remove_path",
    [
        "cover_sheet.implementing_division",
        "cover_sheet.title_of_activity",
        "cover_sheet.brief_description",
        "cover_sheet.proposed_budget",
        "cover_sheet.focal_point_name",
        "cover_sheet.focal_point_email",
        "problem_analysis.problem_analysis",
        "desa_mandate[0].mandate",
        "desa_mandate[0].contribution",
        "sdgs.sdg_targets",
        "target_group.target_group",
        "capacities[0].capacity",
        "capacities[0].indicator",
        "activities[0].activity_title",
        "financials.total",
    ],
)
def test_rptc_activity_proposal_missing_required_field_is_caught(rptc_schema, sdg_framework, remove_path):
    artifact = build_valid_rptc_artifact(rptc_schema)
    values = copy.deepcopy(artifact.values)

    if remove_path == "cover_sheet.implementing_division":
        del values["cover_sheet"]["implementing_division"]
    elif remove_path == "cover_sheet.title_of_activity":
        del values["cover_sheet"]["title_of_activity"]
    elif remove_path == "cover_sheet.brief_description":
        del values["cover_sheet"]["brief_description"]
    elif remove_path == "cover_sheet.proposed_budget":
        del values["cover_sheet"]["proposed_budget"]
    elif remove_path == "cover_sheet.focal_point_name":
        del values["cover_sheet"]["focal_point_name"]
    elif remove_path == "cover_sheet.focal_point_email":
        del values["cover_sheet"]["focal_point_email"]
    elif remove_path == "problem_analysis.problem_analysis":
        del values["problem_analysis"]["problem_analysis"]
    elif remove_path == "desa_mandate[0].mandate":
        del values["desa_mandate"][0]["mandate"]
    elif remove_path == "desa_mandate[0].contribution":
        del values["desa_mandate"][0]["contribution"]
    elif remove_path == "sdgs.sdg_targets":
        del values["sdgs"]["sdg_targets"]
    elif remove_path == "target_group.target_group":
        del values["target_group"]["target_group"]
    elif remove_path == "capacities[0].capacity":
        del values["capacities"][0]["capacity"]
    elif remove_path == "capacities[0].indicator":
        del values["capacities"][0]["indicator"]
    elif remove_path == "activities[0].activity_title":
        del values["activities"][0]["activity_title"]
    elif remove_path == "financials.total":
        del values["financials"]["total"]
    else:
        raise AssertionError(f"unhandled remove_path: {remove_path}")

    artifact.values = values
    report = validate_artifact(rptc_schema, artifact, sdg_framework)

    assert report.is_valid is False
    assert remove_path in report.missing
