# Phase 2 Backlog — Deferred Findings from Phase 1 Final Review

These items were identified by the Phase 1 whole-branch review (2026-06-27). None
block Phase 1; they are logged here so they are addressed deliberately, not
rediscovered later.

## Important (carry into Phase 2)

1. **`budget_table` is a required field with no shape validation.**
   `schemas/da-concept-note.v19.json` declares `budget_summary` (and
   `consultancy_requirements`) as `type: budget_table, required: true`, but
   `field_validators.validate_field_value` has no `budget_table` branch, so any
   non-empty value of any shape passes as valid (required-emptiness *is* still
   enforced). Phase 2 should add a `budget_table` sub-schema to the models
   (typed rows/columns + computed totals) and a validator branch, replacing the
   row/column shape currently described only in `guidance` text.

2. **Completeness counting can report 100% on an empty required repeating section.**
   `validation.validate_artifact` increments `required_total` per *existing*
   repeating item, so a repeating section with zero items contributes 0 — an
   artifact with no outcomes/outputs can report `required_filled == required_total`.
   Phase 2 should add a section-level `min_items` (or required-section) concept to
   the `Section` model and count required repeating sections as expecting ≥1 item.
   This metric will drive the Phase 2 conversation/UI progress indicator, so it
   must be accurate.

## Minor (nice to have)

- `SDGFramework._index()` rebuilds the lookup dict on every call; cache via
  `functools.cached_property` (or compute once in the SDG validator) for bulk use.
- `Issue.severity` is a bare `str`; make it `Literal["error","warning"]` (or an enum)
  so a typo'd severity can't silently bypass `ValidationReport.is_valid`.
- Field types `DATE`, `QUARTER_YEAR`, `GA_RESOLUTION_LIST`, `BUDGET_TABLE`,
  `RATING_SCALE` fall through `field_validators` with no validation this phase
  (intentional). Add per-type validation as Phase 2 needs it.
- `options=None` on a select means "unconstrained" (accepts any value). Confirm the
  RPTC `countries` field's `options: []` (empty list, rejects everything) is intended
  vs. should be unconstrained until a country list is supplied.
- DA `goe_125` is `rich_text` while peer budget classes are `repeating_group`;
  revisit when building budget aggregation/export.
- RPTC: `quarter_year` fields are named `*_quarter`; consider renaming. The Annexes
  section was omitted (template body truncated) — add a minimal section if needed.
- Consider package-level exports in `cidy/__init__.py`
  (`validate_artifact`, `load_schema_file`, `load_sdg_framework_file`, …) to give the
  Phase 2 API layer a stable import surface.
