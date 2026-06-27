# CIdy Drafting Companion — Requirements

**Status:** Draft v1
**Date:** 2026-06-27
**Owner:** Ronen

---

## 1. Overview

CIdy Drafting Companion ("CIdy") is a cloud-hosted, multi-user web application that
helps users draft UN funding/project artifacts through a guided, conversational
interface. Users select the fund they are preparing an artifact for, answer guided
questions, and CIdy assembles a coherent, clear, submission-ready document grounded in
the official templates and guidelines.

CIdy assists — it does not replace the drafter's judgment. The user remains the author
and approves all content.

### 1.1 Goals

- Reduce the time and expertise needed to produce a well-formed funding artifact.
- Enforce structural completeness and adherence to each fund's template and guidelines.
- Improve coherence and clarity across sections (objective ↔ outcomes ↔ budget, etc.).
- Help users select relevant SDG targets and align with GA resolutions.
- Lay groundwork for assisted costing and cross-artifact alignment from a corpus of past
  projects.

### 1.2 Non-goals (v1)

- Real-time, simultaneous co-editing (Google-Docs style).
- Pixel-perfect replication of the official `.docx` styling (clean, section-faithful
  output is sufficient — see §6).
- Submission/workflow integration with UN internal systems.
- Assisted costing and cross-artifact alignment as *working* features (scaffolded only;
  see §8).

---

## 2. Users

| User type | Description | Primary needs |
|-----------|-------------|---------------|
| Drafter | DESA/division staff preparing a proposal, concept note, or report. | Guided drafting, coherence checks, save/resume, export. |
| Collaborator | Colleague invited to contribute to or revise an artifact. | Shared (sequential) editing, review current state, export. |
| Reviewer (read/export) | Person who needs to read or export but not edit. | View live preview, export Word/PDF/JSON. |

There is no separate admin role in v1. Reference data (SDG framework, template schemas)
is managed by maintainers out-of-band.

---

## 3. Supported funds & artifact types

CIdy is template-driven: each artifact type is described by a **Template Schema** (a
versioned JSON form-definition derived from the official `.docx` template and its
guidelines). Adding a fund or artifact type is a data task, not a code change.

**v1 supported artifact types:**

| Fund | Artifact type | Source template |
|------|---------------|-----------------|
| Development Account (DA) | Concept Note (19th tranche) | `T19 Annex 1 - Template for Concept Notes.docx` |
| RPTC | Activity Proposal | `rptc_activity_proposal_template_docx_2.docx` |
| RPTC | Activity Report | `rptc_activity_report_template_v_2026_05_21_0.docx` *(fast-follow; same mechanism)* |

**Reference guidelines used to ground guidance and validation:**

- `Guidelines Concept Notes 19th tranche final 19 9 2025.docx` (DA)
- `rptc_guidelines_20233.docx` (RPTC)

**Future:** additional funds/tranches added by supplying new Template Schemas + guidelines.

### 3.1 Representative artifact structure

The Template Schemas must capture the real structure of these forms, including fixed
sections, repeating groups, dropdown/checkbox fields, and budget tables. Examples:

- **DA Concept Note:** Background (max 1.5 pages), Title, Implementing/joint/collaborating
  entities, Relationship to SDGs (targets in ascending order, max 10), Objective, Project
  plan, Expected progress & performance measures, Budget summary (Other staff costs,
  Consultants, Travel of staff, Contractual services, General operating expenses, Grants &
  contributions, Total), fascicle data (SIDS/LLDC/LDC, regions, SDGs 1–17, partnership
  types, consultancy requirements, deliverables), Outcomes & Outputs (OC1 → OP1.1…), UN
  system coordination / RCO engagement, Partnerships, and a detailed Budget narrative by
  budget class (015, 105, 115, 120, 125, 145).
- **RPTC Activity Proposal:** Cover sheet (Project ID, Implementing Division, Branch,
  brief description ≤300 words, proposed budget, time frame, focal point, geographic level
  & countries, nature of demand, meeting type, venue, signatures), Title, Problem analysis,
  DESA mandate & expected results, Recipient country request, SDGs (targets), Themes/
  sub-themes, Target group, Capacities to be developed (capacity + indicator, repeating),
  Main activities & timelines (repeating), Coherence & complementary work, Gender/human
  rights/disability/LNOB (gender & disability ratings 0/1/2a/2b), Inputs (DESA/recipient/
  other; in-kind/cash), Financial requirements (staff travel, participants travel,
  consultants, conference services, total), Annexes.

---

## 4. Functional requirements

### 4.1 Fund & artifact selection
- **FR-1** The user can start a new artifact by choosing a fund and artifact type from the
  available Template Schemas.
- **FR-2** The system loads the corresponding Template Schema and initializes an empty
  canonical artifact.

### 4.2 Guided conversational drafting
- **FR-3** CIdy presents a guided, section-by-section conversation derived from the
  Template Schema and grounded in the fund's guidelines.
- **FR-4** For each field, CIdy asks a question, shows the relevant guideline instruction,
  and accepts the user's input.
- **FR-5** CIdy uses the configured LLM to shape raw user input into the artifact's formal
  language and to flag missing, weak, or out-of-spec content (e.g., exceeding a length
  limit such as "Background max 1.5 pages" or "brief description ≤300 words").
- **FR-6** The user can **jump or skip** to any section/field at any time via a navigator;
  drafting is never forced linear.
- **FR-7** CIdy supports repeating groups (e.g., multiple Outcomes/Outputs, capacities,
  activities, consultants, budget line items).

### 4.3 Coherence, clarity & validation
- **FR-8** The user can run a coherence/clarity check that evaluates the whole artifact
  against guideline-derived rules (cross-section consistency, formatting, required fields,
  length limits).
- **FR-9** The system reports completeness (which required fields/sections remain) and
  surfaces warnings/suggestions without blocking the user from saving.

### 4.4 SDG alignment
- **FR-10** The full SDG framework (17 goals, 169 targets, with indicators) is available as
  structured reference data.
- **FR-11** Based on the artifact's problem/objective text, CIdy suggests relevant SDG
  targets; the user confirms or edits the selection.
- **FR-12** SDG selections are stored in the canonical model and rendered per template
  conventions (e.g., DA: targets listed in ascending order, max 10).

### 4.5 GA-resolution alignment
- **FR-13** CIdy performs a real-time web search (via the LLM's retrieval capability) for
  GA resolutions relevant to the artifact and returns candidates **with citations/links**.
- **FR-14** The user confirms which resolutions to cite; selections are stored in the
  canonical model.

### 4.6 Live preview / review
- **FR-15** The user can review the current state of the document at any time as a live
  preview rendered from the canonical model, always reflecting the latest content.

### 4.7 Save, resume & versioning
- **FR-16** Artifacts are autosaved server-side; the user can resume any in-progress
  artifact.
- **FR-17** The system retains version history so the user can view and restore prior
  states.

### 4.8 Collaboration (shared, sequential)
- **FR-18** An artifact has an owner who can invite collaborators (edit) and reviewers
  (read/export).
- **FR-19** Multiple collaborators may edit the same artifact at different times. Editing
  is sequential, not simultaneous; the system prevents silent overwrites via optimistic
  concurrency (the user is warned if the artifact changed since they loaded it).

### 4.9 Import & export
- **FR-20** The user can import an existing `.docx` or `.pdf` artifact; CIdy parses it into
  the canonical model to continue editing (best-effort mapping to the Template Schema).
- **FR-21** The user can export the artifact as **Word (`.docx`)**, **PDF**, and **raw
  JSON**. Exports are generated from the canonical model.
- **FR-22** Exported Word/PDF is clean and section-faithful to the template (correct
  sections, order, tables, and labels) but need not replicate the official styling exactly.
- **FR-23** The user can save/download any export to their local machine.

### 4.10 Account & access
- **FR-24** Users sign in via passwordless **magic link** (email).
- **FR-25** Sessions are time-limited; access to an artifact is restricted to its owner,
  collaborators, and reviewers.

---

## 5. Reference data requirements

- **RD-1** SDG framework (17 goals / 169 targets / indicators) bundled as structured data,
  versioned and updatable without code changes.
- **RD-2** GA resolutions sourced at draft time via real-time LLM web search (no static
  corpus required in v1); results must include citations.
- **RD-3** Template Schemas and guidelines are versioned reference data; an artifact records
  which schema version it was drafted against.

---

## 6. Output / export requirements

- **OR-1** Canonical JSON is the source of truth; Word, PDF, and JSON exports are all
  projections of it (data layer decoupled from presentation layer).
- **OR-2** Word/PDF exports follow the template's sections, order, labels, and tables.
- **OR-3** JSON export contains the complete canonical artifact, suitable for re-import and
  for downstream programmatic use.

---

## 7. Non-functional requirements

- **NFR-1 Extensibility:** new funds/artifact types added via Template Schema + reference
  data only.
- **NFR-2 Provider independence:** the LLM is accessed through an abstraction; the provider
  (default Claude) can be swapped or self-hosted.
- **NFR-3 Resilience:** drafting, saving, and export continue to work when the LLM or web
  search is unavailable; AI suggestions degrade gracefully (retry/queue), never causing
  data loss.
- **NFR-4 Data safety:** autosave plus version history prevent loss of work; concurrency
  guard prevents silent overwrites.
- **NFR-5 Privacy/security:** artifact access is authenticated and authorized; data in
  transit and at rest is encrypted (see technical-requirements §Security).
- **NFR-6 Usability:** the guided conversation, navigator, and live preview are usable
  without training; users can always see where they are and what remains.
- **NFR-7 Auditability:** key actions (edits, exports, collaborator changes) are recorded.

---

## 8. Phasing

| Phase | Contents |
|-------|----------|
| **MVP (v1)** | Magic-link auth; fund/artifact selection (DA Concept Note, RPTC Activity Proposal); guided conversational drafting; coherence/clarity checks; SDG alignment; GA-resolution alignment via live search; live preview; save/resume + version history; shared sequential editing; import + export (Word/PDF/JSON). |
| **Fast-follow** | RPTC Activity Report schema; richer import mapping; org SSO option. |
| **Later** | Assisted costing from the `artifacts/` corpus; cross-artifact alignment (detect overlap/complementarity with existing projects). Data model and interfaces are designed in v1 to accept these without rework; `artifacts/` is currently empty. |

---

## 9. Acceptance criteria (MVP)

- A user can sign in via magic link, create a DA Concept Note or RPTC Activity Proposal,
  and be guided through all required sections.
- The user can jump/skip between sections freely and review a live preview at any time.
- CIdy suggests SDG targets and surfaces cited GA resolutions, which the user can confirm.
- A coherence check reports cross-section issues and remaining required fields.
- Work autosaves; the user can resume later and restore a prior version.
- A second collaborator can edit the same artifact later without silently overwriting
  changes.
- The user can export a clean, section-faithful Word and PDF, and a complete JSON, and
  download them locally.
- The user can import a `.docx`/`.pdf` and continue editing.
