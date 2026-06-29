"""Manual smoke demo for the cidy core library (Phase 1).

Run from the backend/ directory:

    python examples/demo_validate.py

It loads the RPTC Activity Proposal schema and the full SDG framework, builds a
partially-filled artifact, validates it, and prints the validation report so you
can see required-field, constraint, and SDG checks in action.
"""

from pathlib import Path

from cidy.artifact.models import Artifact
from cidy.artifact.validation import validate_artifact
from cidy.reference.sdg import load_sdg_framework_file
from cidy.schema.loader import load_schema_file

ROOT = Path(__file__).resolve().parents[1]  # backend/ root


def main() -> None:
    schema = load_schema_file(ROOT / "schemas" / "rptc-activity-proposal.v2024.json")
    framework = load_sdg_framework_file(ROOT / "data" / "sdg_framework.json")

    print(f"Loaded schema: {schema.title} ({schema.fund}/{schema.artifact_type})")
    print(f"SDG framework: {len(framework.all_target_codes())} targets\n")

    # A deliberately partial draft: brief_description over the 300-word limit is
    # avoided, but several required fields are left empty to show the report.
    artifact = Artifact(
        schema_id=schema.schema_id,
        schema_version=schema.version,
        title="Demo: capacity building on tax cooperation",
        values={
            "cover_sheet": {
                "brief_description": "Strengthen developing-country capacity in "
                "international tax cooperation through training and advisory support.",
                "proposed_budget": 75000,
                # implementing_division and focal_point_* intentionally omitted
            },
            "problem_analysis": {
                "problem_analysis": "Limited institutional capacity to negotiate "
                "and administer cross-border tax rules."
            },
            # RPTC's sdg_targets has no ascending/max-items constraint (unlike the
            # DA Concept Note), so these are only checked for being valid codes.
            "sdgs": {"sdg_targets": ["17.1", "8.5"]},
            "financials": {"total": 75000},
        },
    )

    report = validate_artifact(schema, artifact, framework)

    print(f"is_valid: {report.is_valid}")
    print(f"completeness: {report.required_filled}/{report.required_total} required fields filled")
    print(f"missing required: {report.missing}\n")
    print("issues:")
    for issue in report.issues:
        print(f"  [{issue.severity}] {issue.path}: {issue.message}")


if __name__ == "__main__":
    main()
