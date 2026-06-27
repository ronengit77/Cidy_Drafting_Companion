# CIdy Drafting Companion — Technical Requirements

**Status:** Draft v1
**Date:** 2026-06-27
**Companion to:** `requirements.md`

---

## 1. Architecture overview

CIdy is a serverless, cloud-hosted web application on AWS. The central design principle is
a **canonical JSON artifact model** that is the single source of truth; all presentation
(Word, PDF, JSON, live preview) is a projection of it, and all drafting behavior is driven
by versioned **Template Schemas**.

```
                          ┌──────────────────────────────┐
   Browser (SPA, HTML/JS) │  Guided conversation · Navigator · Live preview · Export UI
   S3 + CloudFront        └──────────────┬───────────────┘
                                         │ HTTPS / JWT
                                  ┌──────▼───────┐
                                  │ API Gateway  │
                                  └──────┬───────┘
                                         │
            ┌───────────────┬────────────┼───────────────┬─────────────────┐
            │               │            │               │                 │
      ┌─────▼─────┐  ┌──────▼─────┐ ┌────▼──────┐ ┌──────▼──────┐  ┌────────▼────────┐
      │  Auth      │  │ Artifacts  │ │ Conversa- │ │ Export/     │  │ LLM Orchestrator │
      │ (magic     │  │ CRUD +     │ │ tion       │ │ Import      │  │ (provider-       │
      │  link)     │  │ versioning │ │ engine     │ │ renderers   │  │  agnostic)       │
      └─────┬──────┘  └──────┬─────┘ └────┬───────┘ └──────┬──────┘  └────────┬────────┘
            │                │            │                │                  │
        ┌───▼────┐      ┌────▼─────────────▼────┐     ┌────▼────┐      ┌──────▼───────┐
        │  SES   │      │ PostgreSQL (Aurora/RDS)│     │   S3    │      │ LLMProvider  │
        │ (email)│      │ users, artifacts(JSONB),│    │ uploads,│      │ (Claude dflt)│
        └────────┘      │ versions, collaborators,│    │ exports,│      │  + web search│
                        │ reference data          │    │ schemas │      └──────────────┘
                        └─────────────────────────┘    └─────────┘
```

All compute is **Python AWS Lambda** behind **API Gateway**.

---

## 2. Components

### 2.1 Frontend (SPA)
- HTML + JavaScript single-page app; vanilla or a lightweight framework (no heavy
  dependency required). Static-hosted on **S3** and served via **CloudFront**.
- Responsibilities: render the guided conversation, the jump/skip section navigator, the
  live preview (rendered from canonical JSON returned by the API), SDG/GA confirmation UI,
  and export/import controls.
- Holds no business rules about template structure — it renders what the Template Schema +
  canonical artifact describe.

### 2.2 API layer (Python Lambda + API Gateway)
Logical function groups (each a Lambda or a route within a Lambda app such as
FastAPI/Chalice on Lambda):
- **Auth** — magic-link request + token verification, session issuance.
- **Artifacts** — create/read/update, list, version history, restore; optimistic
  concurrency.
- **Conversation engine** — given an artifact + Template Schema, returns the next
  question(s), accepts answers, applies LLM shaping/validation.
- **LLM orchestrator** — wraps the `LLMProvider` interface; handles prompting, shaping,
  coherence checks, SDG suggestion, GA web search.
- **Export/Import renderers** — produce `.docx`, PDF, JSON from canonical model; parse
  uploaded `.docx`/`.pdf` into canonical model.
- **Reference data** — serve SDG framework and Template Schemas.

### 2.3 Database — PostgreSQL (Aurora Serverless v2 / RDS)
Stores relational metadata and the canonical artifacts as `JSONB`. See §4.

### 2.4 Object storage — S3
Buckets/prefixes for: uploaded source documents (import), generated exports, Template
Schemas, SDG reference data, and (future) the `artifacts/` corpus for costing/alignment.

### 2.5 Email — SES
Sends magic-link sign-in emails.

### 2.6 LLM — provider-agnostic
Accessed only through `LLMProvider` (§6). Default implementation targets Claude via the
Anthropic API; the interface also exposes a web-search/retrieval capability for GA
resolutions.

---

## 3. Template Schema (form-definition)

A Template Schema is the versioned JSON description of one artifact type, derived offline
from the official `.docx` template and its guidelines. It drives the conversation,
validation, preview, and export — the app never parses raw template `.docx` at runtime.

### 3.1 Ingestion (offline/build-time)
- A tooling step parses each `.docx` template (sections, headings, content-control fields,
  dropdowns/checkboxes, budget tables, embedded `<<Instructions>>`) and the guidelines into
  a Template Schema JSON, reviewed by a maintainer and committed/versioned.
- Output is stored in S3 and registered in the `template_schemas` table.

### 3.2 Schema shape (illustrative)
```json
{
  "schema_id": "da-concept-note",
  "version": "19th-tranche-2025-09",
  "fund": "DA",
  "artifact_type": "concept_note",
  "title": "Template for Concept Notes (19th Tranche)",
  "sections": [
    {
      "id": "background",
      "title": "Background",
      "guidance": "Max 1.5 pages. Includes title, implementing entities, objective…",
      "constraints": { "max_pages": 1.5 },
      "fields": [
        { "id": "fascicle_title", "label": "Fascicle Note Title", "type": "text",
          "required": true },
        { "id": "implementing_entity", "label": "Implemented by", "type": "text",
          "required": true },
        { "id": "sdg_targets", "label": "Relationship to SDGs",
          "type": "sdg_target_list", "max_items": 10, "order": "ascending" },
        { "id": "objective", "label": "Objective", "type": "rich_text",
          "required": true }
      ]
    },
    {
      "id": "outcomes_outputs",
      "title": "Outcomes and Outputs",
      "type": "repeating_group",
      "item": {
        "fields": [
          { "id": "outcome", "label": "Outcome (OC)", "type": "rich_text" },
          { "id": "outputs", "type": "repeating_group",
            "item": { "fields": [ { "id": "output", "type": "rich_text" } ] } }
        ]
      }
    }
  ]
}
```

### 3.3 Field types (initial set)
`text`, `rich_text`, `number`, `currency`, `boolean` (Yes/No), `single_select`,
`multi_select`, `checkbox_group`, `date`, `quarter_year`, `sdg_target_list`,
`ga_resolution_list`, `repeating_group`, `budget_table` (typed rows with computed totals),
`rating_scale` (e.g., gender/disability 0/1/2a/2b).

Each field/section may carry: `guidance` (from guidelines), `required`, `constraints`
(length/page/word limits), `validation` rules, and `help_examples`.

---

## 4. Data model

### 4.1 Canonical artifact (JSONB)
The artifact's content is a single JSON object keyed by the schema's section/field ids:
```json
{
  "schema_id": "rptc-activity-proposal",
  "schema_version": "2024",
  "values": {
    "cover.brief_description": "…",
    "cover.proposed_budget": 75000,
    "sdgs.targets": ["8.5", "8.6"],
    "ga_resolutions": [
      { "symbol": "A/RES/78/…", "title": "…", "url": "https://…" }
    ],
    "capacities": [
      { "capacity": "Increased knowledge of …", "indicator": "80% of participants …" }
    ],
    "financials": {
      "staff_travel": 12000, "participants_travel": 30000,
      "consultants": 20000, "conference_services": 13000, "total": 75000
    }
  }
}
```
Validation and rendering are always interpreted against the artifact's `schema_version`.

### 4.2 Relational tables (PostgreSQL)
| Table | Key columns |
|-------|-------------|
| `users` | id, email, created_at, last_login |
| `auth_tokens` | id, user_id, token_hash, expires_at, consumed_at |
| `template_schemas` | schema_id, version, fund, artifact_type, s3_key, is_active |
| `artifacts` | id, owner_id, schema_id, schema_version, title, status, **content (JSONB)**, **version_no**, created_at, updated_at |
| `artifact_versions` | id, artifact_id, version_no, content (JSONB), author_id, created_at |
| `artifact_collaborators` | artifact_id, user_id, role (`editor`/`reviewer`) |
| `reference_sdg` | goal, target, indicator, text (seed data) |
| `exports` | id, artifact_id, format, s3_key, created_at |
| `audit_log` | id, actor_id, artifact_id, action, detail (JSONB), created_at |

`content` is `JSONB` to allow indexing/querying and schema-flexible storage.

### 4.3 Concurrency & versioning
- Optimistic concurrency: each save sends the `version_no` the client loaded. The API
  rejects the write if it no longer matches current (`409 Conflict`), prompting the client
  to reload/merge. On success, `version_no` increments and the prior content is written to
  `artifact_versions`.
- Autosave issues periodic saves; only changed content is persisted.

---

## 5. API surface (representative)

| Method & path | Purpose |
|---------------|---------|
| `POST /auth/magic-link` | Request a sign-in link (SES email). |
| `POST /auth/verify` | Exchange token for a session JWT. |
| `GET /schemas` | List available Template Schemas. |
| `GET /schemas/{id}` | Fetch a Template Schema. |
| `POST /artifacts` | Create artifact from a schema. |
| `GET /artifacts` | List artifacts the user can access. |
| `GET /artifacts/{id}` | Fetch canonical artifact + current `version_no`. |
| `PUT /artifacts/{id}` | Save content (optimistic concurrency). |
| `GET /artifacts/{id}/versions` | List versions; `…/versions/{n}` to fetch/restore. |
| `POST /artifacts/{id}/conversation/next` | Get next guided question(s). |
| `POST /artifacts/{id}/conversation/answer` | Submit an answer; returns shaped value + flags. |
| `POST /artifacts/{id}/check` | Run coherence/clarity + completeness check. |
| `POST /artifacts/{id}/sdg/suggest` | Suggest SDG targets from current content. |
| `POST /artifacts/{id}/ga/search` | Live web search for GA resolutions (cited). |
| `GET /artifacts/{id}/preview` | Rendered preview (HTML) from canonical model. |
| `POST /artifacts/{id}/export?format=docx\|pdf\|json` | Generate + return export. |
| `POST /artifacts/{id}/collaborators` | Add/remove collaborator/reviewer. |
| `POST /artifacts/import` | Upload `.docx`/`.pdf` → canonical artifact. |

All non-auth endpoints require a valid session JWT and enforce per-artifact authorization.

---

## 6. LLM abstraction

```python
class LLMProvider(Protocol):
    def complete(self, messages: list[Message], *, tools=None,
                 max_tokens: int = ...) -> Completion: ...
    def web_search(self, query: str, *, max_results: int = ...) -> list[SearchResult]: ...
```

- **Default implementation:** Claude via the Anthropic API. Use current, capable Claude
  models (e.g., Opus/Sonnet 4.x); GA-resolution lookup uses Claude's web-search/tool-use
  capability so results carry citations. *(Confirm exact model IDs/pricing against the
  current Anthropic docs at implementation time — see the `claude-api` reference.)*
- **Swappable:** alternative providers (OpenAI, self-hosted) implement the same interface.
- **Use sites:** input shaping (raw answer → formal artifact prose), coherence/clarity
  checks, SDG-target suggestion, GA-resolution search. All are advisory; the user confirms.
- **Resilience:** LLM/web-search failures are caught; the affected feature returns a
  "temporarily unavailable, retry" state and never blocks drafting, saving, or export.
- **Prompt grounding:** prompts include the relevant Template Schema guidance and guideline
  text so output respects the fund's conventions and limits.

---

## 7. Rendering & export pipeline

Presentation is fully decoupled from data. A single set of renderers reads the canonical
artifact + Template Schema:

- **HTML preview** — server-rendered (or schema-driven client render) for live review.
- **Word (`.docx`)** — generated with `python-docx`, producing a clean, section-faithful
  document (correct sections, order, labels, tables); not a pixel replica of the official
  styling.
- **PDF** — generated from the canonical model via an HTML→PDF path (e.g., WeasyPrint) or
  from the generated docx.
- **JSON** — the complete canonical artifact (re-importable).

**Import** parses an uploaded `.docx` (via `python-docx`) or `.pdf` (text extraction) and
maps content to the Template Schema on a best-effort basis, leaving unmapped content
flagged for the user.

Renderers run in Lambda; large/slow exports write to S3 and return a download URL.

---

## 8. Security

- **Auth:** passwordless magic link; tokens are single-use, short-TTL, stored hashed.
  Sessions are short-lived JWTs (refresh as needed).
- **Authorization:** every artifact request checks owner/collaborator/reviewer membership.
- **Encryption:** TLS in transit; S3 and RDS encrypted at rest (KMS).
- **Secrets:** LLM API keys and DB credentials in AWS Secrets Manager; never in client or
  repo.
- **Input handling:** uploaded files scanned/size-limited; parsing sandboxed in Lambda.
- **Auditability:** `audit_log` records edits, exports, and collaborator changes.
- **Data handling with LLM:** artifact content sent to the LLM provider is governed by
  provider data-use terms; the provider is configurable to meet org requirements.

---

## 9. Non-functional & operational

- **Extensibility:** new fund/artifact = new Template Schema + reference data; no core code
  change.
- **Statelessness:** Lambdas are stateless; all state in Postgres/S3.
- **Cost/scaling:** serverless scales to load; Aurora Serverless v2 for variable demand.
- **Observability:** structured logs (CloudWatch), metrics on LLM latency/failures and
  export success.
- **Testing strategy:**
  - Template-schema ingestion validated against the real `.docx` templates.
  - Renderers tested by round-tripping canonical JSON → docx/pdf/json.
  - Conversation engine tested as a pure state machine with the LLM mocked.
  - Concurrency tested for the optimistic-locking conflict path.
- **CI/CD:** infrastructure as code (e.g., SAM/CDK/Terraform); automated tests gate deploys.

---

## 10. Future-proofing for costing & cross-artifact alignment (scaffolded)

The model and interfaces anticipate later phases without committing implementation now:
- The `artifacts/` corpus (S3) and a future retrieval index (embeddings) will back
  **assisted costing** (estimate budget lines from comparable past projects) and
  **cross-artifact alignment** (detect overlap/complementarity).
- The `LLMProvider` web-search/retrieval surface and the canonical financial sub-model
  (`budget_table` fields, typed totals) are designed so these features attach to existing
  structures rather than requiring schema changes.
- `artifacts/` is currently empty; these features are inert until a corpus exists.
