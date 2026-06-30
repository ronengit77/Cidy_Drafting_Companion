# CIdy Phase 4 — AI SDG-Target Suggestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an advisory endpoint that suggests relevant SDG targets for an artifact — grounded in the project's content and validated against the official 169-target framework — using the existing provider-agnostic LLM interface.

**Architecture:** A pure service function (`suggest_sdg_targets`) builds a prompt from the artifact's rendered content plus the official SDG goal/target list, asks the LLM for a JSON list of `{target, rationale}`, parses it tolerantly, and **validates every returned code against the `SDGFramework`** (dropping invalid/duplicate codes and attaching the official target text as the title). A new `POST /artifacts/{id}/assist/sdg-suggest` endpoint (read access, advisory — never mutates) returns the validated suggestions; the user applies them via the existing `PUT /artifacts/{id}`. GA-resolution search is deferred to a later phase.

**Tech Stack:** Python 3.12, FastAPI, OpenAI SDK (active provider), Pydantic v2, pytest. Reuses Phases 1/2A/2B/3.

## Global Constraints

- Python version floor: **3.12**.
- Reuse the Phase 3 `LLMProvider` Protocol — the service depends only on it (no `openai` import in the service). Default model stays `gpt-4o-mini` (config).
- Every suggested target code MUST be validated against the framework (`SDGFramework.has_target`) before being returned; invalid or duplicate codes are dropped. The returned `title` is the official target text from the framework, never the model's wording.
- Advisory only: the endpoint never writes to the artifact (no `commit`/`content=`). Read access (`authz.require_artifact(..., "read")`).
- Graceful degradation: 503 when no provider is configured or a provider call fails (`LLMError`); if the model output cannot be parsed into suggestions, return an **empty list with HTTP 200** (not an error).
- **No real OpenAI calls in the default test suite** — tests use small stub providers returning canned JSON / the Echo double. The SDG reference data is the real bundled `data/sdg_framework.json` (loaded via `schema_registry.get_sdg_framework`).
- New code under `backend/cidy_api/`; tests under `backend/tests/api/`. The Phase 1 `cidy` package MUST NOT be modified. Extend only `dto.py`, `routers/assist.py`, and (if needed) reuse `cidy_api/llm/assist.py`'s `render_artifact_summary`.
- Tests run against the already-running local Postgres over TCP. Do NOT run `docker`/`sam` from Git Bash.
- TDD: failing test first. Commit after each task with a `feat:` prefixed message, staging specific files (never `git add -A`).

## Prerequisites

On a branch containing Phases 1/2A/2B/3 (`phase4-sdg-suggestion`, cut from `master` after PR #5). Before Task 1, confirm `cd backend && python -m pytest -q` is green (145 passed, 1 skipped).

## File Structure

```
backend/cidy_api/llm/sdg_suggest.py            # SDGSuggestion, _extract_json, suggest_sdg_targets (NEW)
backend/cidy_api/dto.py                         # + SDGSuggestionOut, SDGSuggestResponse (EDIT)
backend/cidy_api/routers/assist.py              # + POST /{id}/assist/sdg-suggest (EDIT)
backend/tests/api/test_sdg_suggest_service.py   (NEW)
backend/tests/api/test_sdg_suggest_endpoint.py  (NEW)
```

---

### Task 1: SDG suggestion service

**Files:**
- Create: `backend/cidy_api/llm/sdg_suggest.py`
- Create: `backend/tests/api/test_sdg_suggest_service.py`

**Interfaces:**
- Consumes: `LLMProvider` (Phase 3); `SDGFramework` (Phase 1, `has_target`/`get_target`/`goals`).
- Produces:
  - `sdg_suggest.SDGSuggestion` — dataclass with `target: str`, `title: str`, `rationale: str`.
  - `sdg_suggest._extract_json(text: str) -> dict` — tolerant JSON extraction (strips ```` ``` ```` fences, takes the first `{`…last `}`); returns `{}` on failure.
  - `sdg_suggest.suggest_sdg_targets(provider, framework, *, fund: str, artifact_type: str, context: str, max_suggestions: int = 8) -> list[SDGSuggestion]` — prompts for JSON `{"suggestions": [{"target","rationale"}]}`, parses, validates each code against `framework`, drops invalid/duplicate, attaches the official target text as `title`, caps at `max_suggestions`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_sdg_suggest_service.py`:
```python
from cidy.reference.sdg import load_sdg_framework

from cidy_api.llm import sdg_suggest

FRAMEWORK = load_sdg_framework(
    {
        "goals": [
            {"goal": 1, "title": "No Poverty", "targets": [{"target": "1.1", "text": "End extreme poverty"}]},
            {"goal": 8, "title": "Decent Work", "targets": [
                {"target": "8.5", "text": "Full and productive employment"},
                {"target": "8.6", "text": "Reduce youth NEET"},
            ]},
        ]
    }
)


class _StubProvider:
    def __init__(self, output: str) -> None:
        self._output = output
        self.last_system = None
        self.last_user = None

    def complete(self, system, user, *, max_tokens=600, temperature=0.3):
        self.last_system = system
        self.last_user = user
        return self._output


def _suggest(output):
    return sdg_suggest.suggest_sdg_targets(
        _StubProvider(output), FRAMEWORK,
        fund="RPTC", artifact_type="activity_proposal", context="jobs for youth",
    )


def test_valid_codes_attached_with_official_title():
    out = _suggest('{"suggestions": [{"target": "8.5", "rationale": "jobs"}]}')
    assert len(out) == 1
    assert out[0].target == "8.5"
    assert out[0].title == "Full and productive employment"  # framework text, not the model's
    assert out[0].rationale == "jobs"


def test_invalid_codes_dropped():
    out = _suggest('{"suggestions": [{"target": "8.5", "rationale": "a"}, {"target": "99.9", "rationale": "b"}]}')
    assert [s.target for s in out] == ["8.5"]


def test_duplicates_dropped():
    out = _suggest('{"suggestions": [{"target": "8.5", "rationale": "a"}, {"target": "8.5", "rationale": "b"}]}')
    assert [s.target for s in out] == ["8.5"]


def test_tolerant_of_code_fences():
    out = _suggest('```json\n{"suggestions": [{"target": "1.1", "rationale": "poverty"}]}\n```')
    assert [s.target for s in out] == ["1.1"]


def test_unparseable_output_returns_empty():
    assert _suggest("sorry, I cannot help") == []


def test_prompt_grounds_on_targets_and_context():
    p = _StubProvider('{"suggestions": []}')
    sdg_suggest.suggest_sdg_targets(
        p, FRAMEWORK, fund="RPTC", artifact_type="activity_proposal", context="youth employment",
    )
    assert "8.5" in p.last_user  # official targets listed
    assert "youth employment" in p.last_user  # project context included
    assert "JSON" in p.last_system
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_sdg_suggest_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.llm.sdg_suggest'`.

- [ ] **Step 3: Implement the service**

`backend/cidy_api/llm/sdg_suggest.py`:
```python
from __future__ import annotations

import json
from dataclasses import dataclass

from cidy.reference.sdg import SDGFramework
from cidy_api.llm.base import LLMProvider


@dataclass
class SDGSuggestion:
    target: str
    title: str
    rationale: str


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def suggest_sdg_targets(
    provider: LLMProvider,
    framework: SDGFramework,
    *,
    fund: str,
    artifact_type: str,
    context: str,
    max_suggestions: int = 8,
) -> list[SDGSuggestion]:
    goals_list = "\n".join(
        f"Goal {g.goal} ({g.title}): " + ", ".join(t.target for t in g.targets)
        for g in framework.goals
    )
    system = (
        f"You are aligning a {fund} {artifact_type} with the UN Sustainable Development Goals. "
        f"From the project's content, identify the most relevant SDG TARGETS (e.g. '8.5'). "
        f"Choose ONLY from the official target codes provided. Suggest at most {max_suggestions}. "
        f'Respond with ONLY a JSON object of the form '
        f'{{"suggestions": [{{"target": "<code>", "rationale": "<one short sentence>"}}]}}.'
    )
    user = (
        f"Official SDG targets by goal:\n{goals_list}\n\n"
        f"Project content:\n{context or '(empty draft)'}"
    )
    raw = provider.complete(system, user, max_tokens=700)
    data = _extract_json(raw)

    suggestions: list[SDGSuggestion] = []
    seen: set[str] = set()
    for item in data.get("suggestions", []):
        if not isinstance(item, dict):
            continue
        code = str(item.get("target", "")).strip()
        if not code or code in seen or not framework.has_target(code):
            continue
        seen.add(code)
        target = framework.get_target(code)
        suggestions.append(
            SDGSuggestion(
                target=code,
                title=target.text if target else "",
                rationale=str(item.get("rationale", "")).strip(),
            )
        )
        if len(suggestions) >= max_suggestions:
            break
    return suggestions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_sdg_suggest_service.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/llm/sdg_suggest.py backend/tests/api/test_sdg_suggest_service.py
git commit -m "feat: add SDG-target suggestion service with framework validation"
```

---

### Task 2: SDG-suggest endpoint

**Files:**
- Modify: `backend/cidy_api/dto.py` (add response DTOs)
- Modify: `backend/cidy_api/routers/assist.py` (add the route)
- Create: `backend/tests/api/test_sdg_suggest_endpoint.py`

**Interfaces:**
- Consumes: `suggest_sdg_targets`/`SDGSuggestion` (Task 1); `schema_registry.get_schema`/`get_sdg_framework` (Phase 2B); `assist.render_artifact_summary` (Phase 3); `authz.require_artifact`, `get_current_user`, `get_session`, `get_llm_provider`, `LLMError` (Phases 2A/2B/3).
- Produces:
  - `dto.SDGSuggestionOut` (`target: str`, `title: str`, `rationale: str`), `dto.SDGSuggestResponse` (`suggestions: list[SDGSuggestionOut]`).
  - Route `POST /artifacts/{artifact_id}/assist/sdg-suggest` — read access; 503 if no provider; 500 if schema missing; `LLMError` → 503; builds the project context via `render_artifact_summary` and returns validated suggestions. Advisory — no mutation.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_sdg_suggest_endpoint.py`:
```python
from cidy_api.llm.deps import get_llm_provider


class _StubProvider:
    def __init__(self, output):
        self._output = output

    def complete(self, system, user, *, max_tokens=600, temperature=0.3):
        return self._output


def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _new_artifact(client, t):
    resp = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "t"}, headers=_auth(t)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_sdg_suggest_returns_validated_targets(client):
    # 8.5 is a real code in the bundled 169-target framework
    client.app.dependency_overrides[get_llm_provider] = lambda: _StubProvider(
        '{"suggestions": [{"target": "8.5", "rationale": "employment focus"}, {"target": "99.9", "rationale": "bogus"}]}'
    )
    t = _login(client, "sdg1@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(f"/artifacts/{aid}/assist/sdg-suggest", headers=_auth(t))
    assert resp.status_code == 200, resp.text
    targets = [s["target"] for s in resp.json()["suggestions"]]
    assert targets == ["8.5"]  # bogus 99.9 dropped
    assert resp.json()["suggestions"][0]["title"]  # official title attached


def test_sdg_suggest_503_when_llm_not_configured(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: None
    t = _login(client, "sdg2@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(f"/artifacts/{aid}/assist/sdg-suggest", headers=_auth(t))
    assert resp.status_code == 503


def test_sdg_suggest_requires_access(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: _StubProvider('{"suggestions": []}')
    owner = _login(client, "sdg_owner@example.com")
    other = _login(client, "sdg_other@example.com")
    aid = _new_artifact(client, owner)
    resp = client.post(f"/artifacts/{aid}/assist/sdg-suggest", headers=_auth(other))
    assert resp.status_code in (403, 404)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_sdg_suggest_endpoint.py -v`
Expected: FAIL — 404 on the `sdg-suggest` route.

- [ ] **Step 3: Implement DTOs and the route**

Append to `backend/cidy_api/dto.py`:
```python
class SDGSuggestionOut(BaseModel):
    target: str
    title: str
    rationale: str


class SDGSuggestResponse(BaseModel):
    suggestions: list[SDGSuggestionOut]
```

Add to `backend/cidy_api/routers/assist.py`. Extend the existing imports — add to the `cidy_api.dto` import: `SDGSuggestResponse, SDGSuggestionOut`; add `from cidy_api.llm.sdg_suggest import suggest_sdg_targets`; the module already imports `assist`, `schema_registry`, `authz`, `get_session`, `get_current_user`, `get_llm_provider`, `LLMError`, `LLMProvider`, `User`, `status`, `HTTPException`, `Depends`, `uuid`, `Session`. Then add this route:
```python
@router.post("/{artifact_id}/assist/sdg-suggest", response_model=SDGSuggestResponse)
def sdg_suggest(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> SDGSuggestResponse:
    if provider is None:
        raise _NO_LLM
    artifact = authz.require_artifact(session, current_user, artifact_id, "read")
    schema = schema_registry.get_schema(artifact.schema_id)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="artifact references an unknown schema",
        )
    context = assist.render_artifact_summary(schema, artifact.content)
    try:
        results = suggest_sdg_targets(
            provider,
            schema_registry.get_sdg_framework(),
            fund=schema.fund,
            artifact_type=schema.artifact_type,
            context=context,
        )
    except LLMError as exc:
        raise _LLM_DOWN from exc
    return SDGSuggestResponse(
        suggestions=[
            SDGSuggestionOut(target=r.target, title=r.title, rationale=r.rationale) for r in results
        ]
    )
```

- [ ] **Step 4: Run the test and the full suite**

Run: `cd backend && python -m pytest tests/api/test_sdg_suggest_endpoint.py -v && python -m pytest -q`
Expected: `test_sdg_suggest_endpoint.py` PASS (3 tests); full suite (Phases 1/2A/2B/3 + Phase 4) all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/dto.py backend/cidy_api/routers/assist.py backend/tests/api/test_sdg_suggest_endpoint.py
git commit -m "feat: add SDG-target suggestion endpoint"
```

---

## Phase 4 completion

At the end of this plan the backend offers AI SDG-target suggestion: `POST /artifacts/{id}/assist/sdg-suggest` returns SDG targets relevant to the artifact's content, each with the official target title and a short rationale, **validated against the real 169-target framework** so no invalid code is ever returned. It is advisory (the user applies selections via `PUT`), degrades to 503 when the LLM is unavailable, and is fully covered by deterministic tests (no API spend).

## Notes carried forward

- **GA-resolution search** (deferred): live web search for relevant GA resolutions with citations — needs a web-search capability behind its own swappable interface (OpenAI hosted web search, or a dedicated search API). Will attach as another assist endpoint.
- **Apply UX:** the client applies accepted suggestions by writing the codes into the artifact's SDG field via `PUT /artifacts/{id}`. A future convenience endpoint could apply directly (with an explicit confirm).
- **Prompt size:** the suggestion prompt lists all 169 targets; fine for `gpt-4o-mini`. If cost matters later, pass goal titles first and expand on demand.
