# CIdy Phase 3 — LLM-Assisted Drafting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI drafting assistance to the CIdy backend — a provider-agnostic LLM interface (OpenAI as the active implementation) plus two stateless, authenticated endpoints: shape a user's raw answer for a field into the artifact's formal language, and produce a coherence/clarity assessment of the whole artifact.

**Architecture:** A small `cidy_api.llm` package defines an `LLMProvider` Protocol (`complete(system, user) -> str`), a deterministic `EchoLLMProvider` test double, and an `OpenAIProvider` built on the `openai` SDK. A pure-function assist service builds grounded prompts (from the schema's per-field guidance + artifact context) and calls the provider. Two FastAPI endpoints under `/artifacts/{id}/assist/*` expose the features; the provider is supplied via a dependency that returns `None` when no key is configured (→ HTTP 503), so the rest of the app keeps working when the LLM is unavailable. Tests use the Echo/mock providers — no real API calls in the default suite.

**Tech Stack:** Python 3.12, FastAPI, OpenAI Python SDK (v1), Pydantic v2, pytest. Reuses Phases 1/2A/2B.

## Global Constraints

- Python version floor: **3.12**.
- Provider-agnostic: all LLM use goes through the `LLMProvider` Protocol. The OpenAI implementation is the only concrete provider in this phase; it must be swappable.
- Default model is **`gpt-4o-mini`**, overridable via config (`CIDY_LLM_MODEL`). The OpenAI API key is read from the **`OPENAI_API_KEY`** environment variable (already present in the gitignored `.env`); it is NEVER hardcoded or committed.
- **No real OpenAI calls in the default test suite.** Unit/endpoint tests use `EchoLLMProvider` or a mocked client. A single live smoke test is gated behind `CIDY_LLM_LIVE_TESTS=1` and skipped otherwise.
- Assist endpoints are **advisory** — they never mutate the artifact (the client applies a suggestion via the existing `PUT /artifacts/{id}`). Shaping requires `edit` access; coherence requires `read` access.
- Graceful degradation (NFR-3): if no provider is configured → 503 "LLM not configured"; if a provider call fails (`LLMError`) → 503 "LLM temporarily unavailable". Drafting/CRUD endpoints are unaffected.
- New code under `backend/cidy_api/`; tests under `backend/tests/api/`. The Phase 1 `cidy` package MUST NOT be modified. Existing `cidy_api` modules may be extended only where a task says so (`config.py`, `dto.py`, `app.py`, `pyproject.toml`, `backend/requirements.txt`).
- Tests run against the already-running local Postgres over TCP (the `client`/`db_session` fixtures). Do NOT run `docker`/`sam` from Git Bash.
- TDD: failing test first. Commit after each task with a `feat:`/`chore:` prefixed message, staging specific files (never `git add -A`).

## Prerequisites

On a branch containing Phases 1/2A/2B (`phase3-llm-drafting`, cut from `master` after PR #4). The OpenAI API key is in the gitignored `.env` as `OPENAI_API_KEY`. Before Task 1, confirm `cd backend && python -m pytest -q` is green (133 tests).

## File Structure

```
backend/cidy_api/llm/__init__.py            (NEW)
backend/cidy_api/llm/base.py                # LLMProvider Protocol + LLMError (NEW)
backend/cidy_api/llm/fake.py                # EchoLLMProvider (NEW)
backend/cidy_api/llm/openai_provider.py     # OpenAIProvider (NEW)
backend/cidy_api/llm/assist.py              # shape_field, coherence_check, render helper (NEW)
backend/cidy_api/llm/deps.py                # get_llm_provider dependency (NEW)
backend/cidy_api/routers/assist.py          # assist endpoints (NEW)
backend/cidy_api/config.py                  # + openai_api_key, llm_model (EDIT)
backend/cidy_api/dto.py                     # + assist DTOs (EDIT)
backend/cidy_api/app.py                     # + include assist router (EDIT)
backend/pyproject.toml                      # + openai dep (EDIT)
backend/requirements.txt                    # + openai (EDIT, for Lambda)
backend/tests/api/test_llm_provider.py      (NEW)
backend/tests/api/test_openai_provider.py   (NEW)
backend/tests/api/test_assist_service.py    (NEW)
backend/tests/api/test_assist_endpoints.py  (NEW)
```

---

### Task 1: LLM provider interface, Echo double, and config

**Files:**
- Create: `backend/cidy_api/llm/__init__.py`
- Create: `backend/cidy_api/llm/base.py`
- Create: `backend/cidy_api/llm/fake.py`
- Modify: `backend/cidy_api/config.py` (add `openai_api_key`, `llm_model`)
- Create: `backend/tests/api/test_llm_provider.py`

**Interfaces:**
- Consumes: `get_settings`/`Settings` (Phase 2A).
- Produces:
  - `llm.base.LLMProvider` — `runtime_checkable` Protocol with `complete(self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3) -> str`.
  - `llm.base.LLMError(Exception)`.
  - `llm.fake.EchoLLMProvider` — deterministic provider whose `complete` records `last_system`/`last_user` and returns `user` unchanged.
  - `config.Settings.openai_api_key: str` (default `""`, read from env var `OPENAI_API_KEY`) and `config.Settings.llm_model: str` (default `"gpt-4o-mini"`, env `CIDY_LLM_MODEL`).

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_llm_provider.py`:
```python
from cidy_api.llm.base import LLMProvider
from cidy_api.llm.fake import EchoLLMProvider


def test_echo_provider_satisfies_protocol_and_records():
    p = EchoLLMProvider()
    assert isinstance(p, LLMProvider)
    out = p.complete("system text", "user text", max_tokens=10)
    assert out == "user text"
    assert p.last_system == "system text"
    assert p.last_user == "user text"


def test_llm_settings_defaults_and_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    from cidy_api.config import Settings

    s = Settings()
    assert s.llm_model == "gpt-4o-mini"
    assert s.openai_api_key == "sk-test-123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_llm_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.llm'`.

- [ ] **Step 3: Implement the interface, Echo double, and config**

`backend/cidy_api/llm/__init__.py`:
```python
```

`backend/cidy_api/llm/base.py`:
```python
from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Raised when an LLM provider call fails."""


@runtime_checkable
class LLMProvider(Protocol):
    def complete(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3
    ) -> str: ...
```

`backend/cidy_api/llm/fake.py`:
```python
from __future__ import annotations


class EchoLLMProvider:
    """Deterministic provider for tests: echoes the user prompt, records inputs."""

    def __init__(self) -> None:
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3
    ) -> str:
        self.last_system = system
        self.last_user = user
        return user
```

In `backend/cidy_api/config.py`, add `Field` to the pydantic import (`from pydantic import Field`) and add these two fields to the `Settings` class (alongside the existing fields, before the `model_validator`):
```python
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    llm_model: str = "gpt-4o-mini"
```
NOTE: `validation_alias="OPENAI_API_KEY"` makes this field read the un-prefixed `OPENAI_API_KEY` env var (the OpenAI convention, already in `.env`), bypassing the `CIDY_` prefix. `llm_model` keeps the prefix (`CIDY_LLM_MODEL`). If the alias does not resolve from `.env`/env in your pydantic-settings version, switch to `AliasChoices("OPENAI_API_KEY", "CIDY_OPENAI_API_KEY")` — but the test above (which sets the env var) must pass.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_llm_provider.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/llm/__init__.py backend/cidy_api/llm/base.py backend/cidy_api/llm/fake.py backend/cidy_api/config.py backend/tests/api/test_llm_provider.py
git commit -m "feat: add LLM provider interface, echo double, and LLM config"
```

---

### Task 2: OpenAI provider implementation

**Files:**
- Modify: `backend/pyproject.toml` (add `openai`)
- Modify: `backend/requirements.txt` (add `openai` for the Lambda artifact)
- Create: `backend/cidy_api/llm/openai_provider.py`
- Create: `backend/tests/api/test_openai_provider.py`

**Interfaces:**
- Consumes: `llm.base.LLMError` (Task 1).
- Produces:
  - `llm.openai_provider.OpenAIProvider` — `__init__(self, *, api_key: str, model: str, client=None)` (injectable `client` for tests; otherwise constructs `openai.OpenAI(api_key=...)`). `complete(system, user, *, max_tokens=600, temperature=0.3) -> str` calls `client.chat.completions.create(...)` and returns the first choice's message content; wraps any exception in `LLMError`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_openai_provider.py`:
```python
import os
from unittest.mock import MagicMock

import pytest

from cidy_api.llm.base import LLMError
from cidy_api.llm.openai_provider import OpenAIProvider


def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )
    return client


def test_complete_builds_request_and_returns_content():
    client = _mock_client("shaped result")
    p = OpenAIProvider(api_key="x", model="gpt-4o-mini", client=client)
    out = p.complete("sys", "usr", max_tokens=123, temperature=0.1)
    assert out == "shaped result"
    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["max_tokens"] == 123
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][1] == {"role": "user", "content": "usr"}


def test_complete_wraps_errors_in_llm_error():
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("boom")
    p = OpenAIProvider(api_key="x", model="m", client=client)
    with pytest.raises(LLMError):
        p.complete("s", "u")


@pytest.mark.skipif(os.getenv("CIDY_LLM_LIVE_TESTS") != "1", reason="live LLM test disabled")
def test_openai_live_smoke():
    from cidy_api.config import get_settings

    s = get_settings()
    if not s.openai_api_key:
        pytest.skip("no OPENAI_API_KEY configured")
    p = OpenAIProvider(api_key=s.openai_api_key, model=s.llm_model)
    out = p.complete("Reply with exactly the word OK.", "Are you there?")
    assert isinstance(out, str) and out.strip()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_openai_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.llm.openai_provider'` (or `openai`).

- [ ] **Step 3: Add the dependency and implement the provider**

In `backend/pyproject.toml`, add `"openai>=1.30,<2"` to the `dependencies` list.
In `backend/requirements.txt`, add a line `openai>=1.30,<2` (so the Lambda artifact includes it).

`backend/cidy_api/llm/openai_provider.py`:
```python
from __future__ import annotations

from typing import Any

from cidy_api.llm.base import LLMError


class OpenAIProvider:
    def __init__(self, *, api_key: str, model: str, client: Any | None = None) -> None:
        self._model = model
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)

    def complete(
        self, system: str, user: str, *, max_tokens: int = 600, temperature: float = 0.3
    ) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001 - normalize all provider errors
            raise LLMError(str(exc)) from exc
```

- [ ] **Step 4: Install and run the tests**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/api/test_openai_provider.py -v`
Expected: PASS (2 tests; the live smoke test is SKIPPED).

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/requirements.txt backend/cidy_api/llm/openai_provider.py backend/tests/api/test_openai_provider.py
git commit -m "feat: add OpenAI LLM provider implementation"
```

---

### Task 3: Drafting assist service (shape + coherence)

**Files:**
- Create: `backend/cidy_api/llm/assist.py`
- Create: `backend/tests/api/test_assist_service.py`

**Interfaces:**
- Consumes: `LLMProvider` (Task 1); Phase 1 `TemplateSchema`/`Section`/`Field` shapes (`schema.fund`, `schema.artifact_type`, `schema.sections`, `section.id/title/repeating/fields`, `field.id/label/guidance`).
- Produces:
  - `assist.shape_field(provider, *, fund, artifact_type, section_title, field_label, field_guidance, raw_input) -> str` — builds a grounded system prompt and returns the provider's shaped text (stripped).
  - `assist.render_artifact_summary(schema, values) -> str` — renders non-empty values as `"Section / Field: value"` lines (handles repeating sections as `"Section [i] / Field: value"`).
  - `assist.coherence_check(provider, *, schema, values) -> str` — builds a review prompt over the rendered summary and returns the provider's assessment (stripped).

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_assist_service.py`:
```python
from cidy.schema.models import Field, FieldType, Section, TemplateSchema

from cidy_api.llm import assist
from cidy_api.llm.fake import EchoLLMProvider


def _schema() -> TemplateSchema:
    return TemplateSchema(
        schema_id="demo", version="1", fund="RPTC", artifact_type="activity_proposal",
        title="Demo",
        sections=[
            Section(id="cover", title="Cover", fields=[
                Field(id="brief", label="Brief description", type=FieldType.RICH_TEXT,
                      guidance="300 words max; be specific."),
            ]),
            Section(id="caps", title="Capacities", repeating=True, fields=[
                Field(id="capacity", label="Capacity", type=FieldType.RICH_TEXT),
            ]),
        ],
    )


def test_shape_field_grounds_prompt_and_returns_text():
    p = EchoLLMProvider()
    out = assist.shape_field(
        p, fund="RPTC", artifact_type="activity_proposal", section_title="Cover",
        field_label="Brief description", field_guidance="300 words max; be specific.",
        raw_input="we will train tax officials",
    )
    assert out == "we will train tax officials"  # echo returns the user text
    assert "Brief description" in p.last_system
    assert "300 words max" in p.last_system
    assert "RPTC" in p.last_system


def test_render_artifact_summary_includes_values_and_repeats():
    schema = _schema()
    values = {
        "cover": {"brief": "Strengthen capacity"},
        "caps": [{"capacity": "Increased knowledge"}, {"capacity": "Better tools"}],
    }
    summary = assist.render_artifact_summary(schema, values)
    assert "Cover / Brief description: Strengthen capacity" in summary
    assert "Capacities [1] / Capacity: Increased knowledge" in summary
    assert "Capacities [2] / Capacity: Better tools" in summary


def test_coherence_check_reviews_summary():
    p = EchoLLMProvider()
    schema = _schema()
    out = assist.coherence_check(p, schema=schema, values={"cover": {"brief": "X"}})
    assert isinstance(out, str) and out
    assert "coherence" in p.last_system.lower()
    assert "Brief description: X" in p.last_user
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_assist_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.llm.assist'`.

- [ ] **Step 3: Implement the assist service**

`backend/cidy_api/llm/assist.py`:
```python
from __future__ import annotations

from cidy.schema.models import TemplateSchema
from cidy_api.llm.base import LLMProvider


def shape_field(
    provider: LLMProvider,
    *,
    fund: str,
    artifact_type: str,
    section_title: str,
    field_label: str,
    field_guidance: str,
    raw_input: str,
) -> str:
    system = (
        f"You are an expert UN programme officer drafting a {fund} {artifact_type}. "
        f"Rewrite the user's draft for the field '{field_label}' in section '{section_title}' "
        f"into clear, concise, formal language appropriate for this document. "
        f"Follow this guidance: {field_guidance or 'N/A'}. "
        f"Return only the rewritten text, with no preamble or commentary."
    )
    return provider.complete(system, raw_input).strip()


def render_artifact_summary(schema: TemplateSchema, values: dict) -> str:
    lines: list[str] = []
    for section in schema.sections:
        section_values = values.get(section.id)
        if section.repeating and isinstance(section_values, list):
            for i, item in enumerate(section_values, start=1):
                for field in section.fields:
                    value = (item or {}).get(field.id)
                    if value:
                        lines.append(f"{section.title} [{i}] / {field.label}: {value}")
        elif isinstance(section_values, dict):
            for field in section.fields:
                value = section_values.get(field.id)
                if value:
                    lines.append(f"{section.title} / {field.label}: {value}")
    return "\n".join(lines)


def coherence_check(provider: LLMProvider, *, schema: TemplateSchema, values: dict) -> str:
    summary = render_artifact_summary(schema, values)
    system = (
        f"You are reviewing a {schema.fund} {schema.artifact_type} for coherence and clarity. "
        f"Identify inconsistencies, unclear statements, vague claims, and gaps across sections. "
        f"Reference the section and field names. Be concise and specific. "
        f"If the draft reads well, say so briefly."
    )
    user = f"Here is the current draft:\n\n{summary or '(empty draft)'}"
    return provider.complete(system, user, max_tokens=800).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_assist_service.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/llm/assist.py backend/tests/api/test_assist_service.py
git commit -m "feat: add drafting assist service (shape field, coherence check)"
```

---

### Task 4: Assist endpoints and provider dependency

**Files:**
- Create: `backend/cidy_api/llm/deps.py`
- Create: `backend/cidy_api/routers/assist.py`
- Modify: `backend/cidy_api/dto.py` (add assist DTOs)
- Modify: `backend/cidy_api/app.py` (include the assist router)
- Create: `backend/tests/api/test_assist_endpoints.py`

**Interfaces:**
- Consumes: `get_settings` (Phase 2A); `OpenAIProvider` (Task 2); `LLMProvider`/`LLMError` (Task 1); `assist.shape_field`/`coherence_check` (Task 3); `schema_registry.get_schema` (Phase 2B); `authz.require_artifact` (Phase 2B); `get_current_user`/`get_session` (Phase 2A).
- Produces:
  - `llm.deps.get_llm_provider() -> LLMProvider | None` — returns an `OpenAIProvider` when `settings.openai_api_key` is set, else `None`.
  - `dto.ShapeFieldRequest` (`section_id: str`, `field_id: str`, `raw_input: str`), `dto.ShapeFieldResponse` (`shaped_text: str`), `dto.CoherenceResponse` (`assessment: str`).
  - Routes (auth required):
    - `POST /artifacts/{artifact_id}/assist/shape` — `edit` access; 503 if no provider; 400 if the section/field id is unknown; returns shaped text. Advisory only (no mutation).
    - `POST /artifacts/{artifact_id}/assist/coherence` — `read` access; 503 if no provider; returns assessment.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_assist_endpoints.py`:
```python
from cidy_api.llm.deps import get_llm_provider
from cidy_api.llm.fake import EchoLLMProvider


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


def test_shape_returns_text(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    t = _login(client, "assist1@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "brief_description", "raw_input": "train people"},
        headers=_auth(t),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["shaped_text"] == "train people"  # echo


def test_shape_503_when_llm_not_configured(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: None
    t = _login(client, "assist2@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "brief_description", "raw_input": "x"},
        headers=_auth(t),
    )
    assert resp.status_code == 503


def test_shape_unknown_field_400(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    t = _login(client, "assist3@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "nope", "raw_input": "x"},
        headers=_auth(t),
    )
    assert resp.status_code == 400


def test_shape_requires_access(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    owner = _login(client, "assist_owner@example.com")
    other = _login(client, "assist_other@example.com")
    aid = _new_artifact(client, owner)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "brief_description", "raw_input": "x"},
        headers=_auth(other),
    )
    assert resp.status_code in (403, 404)


def test_coherence_returns_assessment(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    t = _login(client, "assist4@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(f"/artifacts/{aid}/assist/coherence", headers=_auth(t))
    assert resp.status_code == 200, resp.text
    assert "assessment" in resp.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_assist_endpoints.py -v`
Expected: FAIL — 404 on the assist routes (router not present).

- [ ] **Step 3: Implement the dependency, DTOs, router, and wiring**

`backend/cidy_api/llm/deps.py`:
```python
from __future__ import annotations

from cidy_api.config import get_settings
from cidy_api.llm.base import LLMProvider
from cidy_api.llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIProvider(api_key=settings.openai_api_key, model=settings.llm_model)
```

Append to `backend/cidy_api/dto.py`:
```python
class ShapeFieldRequest(BaseModel):
    section_id: str
    field_id: str
    raw_input: str


class ShapeFieldResponse(BaseModel):
    shaped_text: str


class CoherenceResponse(BaseModel):
    assessment: str
```

`backend/cidy_api/routers/assist.py`:
```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api import authz, schema_registry
from cidy_api.db import get_session
from cidy_api.deps import get_current_user
from cidy_api.dto import CoherenceResponse, ShapeFieldRequest, ShapeFieldResponse
from cidy_api.llm import assist
from cidy_api.llm.base import LLMError, LLMProvider
from cidy_api.llm.deps import get_llm_provider
from cidy_api.models_db import User

router = APIRouter(prefix="/artifacts", tags=["assist"])

_NO_LLM = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM not configured"
)
_LLM_DOWN = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM temporarily unavailable"
)


@router.post("/{artifact_id}/assist/shape", response_model=ShapeFieldResponse)
def shape(
    artifact_id: uuid.UUID,
    payload: ShapeFieldRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> ShapeFieldResponse:
    if provider is None:
        raise _NO_LLM
    artifact = authz.require_artifact(session, current_user, artifact_id, "edit")
    schema = schema_registry.get_schema(artifact.schema_id)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="artifact references an unknown schema",
        )
    section = next((s for s in schema.sections if s.id == payload.section_id), None)
    if section is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown section_id")
    field = next((f for f in section.fields if f.id == payload.field_id), None)
    if field is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown field_id")
    try:
        shaped = assist.shape_field(
            provider,
            fund=schema.fund,
            artifact_type=schema.artifact_type,
            section_title=section.title,
            field_label=field.label,
            field_guidance=field.guidance,
            raw_input=payload.raw_input,
        )
    except LLMError as exc:
        raise _LLM_DOWN from exc
    return ShapeFieldResponse(shaped_text=shaped)


@router.post("/{artifact_id}/assist/coherence", response_model=CoherenceResponse)
def coherence(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> CoherenceResponse:
    if provider is None:
        raise _NO_LLM
    artifact = authz.require_artifact(session, current_user, artifact_id, "read")
    schema = schema_registry.get_schema(artifact.schema_id)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="artifact references an unknown schema",
        )
    try:
        assessment = assist.coherence_check(provider, schema=schema, values=artifact.content)
    except LLMError as exc:
        raise _LLM_DOWN from exc
    return CoherenceResponse(assessment=assessment)
```

Wire into `backend/cidy_api/app.py`:
```python
from cidy_api.routers import assist as assist_router
```
and in `create_app`:
```python
    app.include_router(assist_router.router)
```

- [ ] **Step 4: Run the test and the full suite**

Run: `cd backend && python -m pytest tests/api/test_assist_endpoints.py -v && python -m pytest -q`
Expected: `test_assist_endpoints.py` PASS (5 tests); full suite (Phases 1/2A/2B + all Phase 3) all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/llm/deps.py backend/cidy_api/routers/assist.py backend/cidy_api/dto.py backend/cidy_api/app.py backend/tests/api/test_assist_endpoints.py
git commit -m "feat: add LLM drafting assist endpoints (shape, coherence)"
```

---

## Phase 3 completion

At the end of this plan the backend offers AI drafting assistance behind a provider-agnostic interface: `POST /artifacts/{id}/assist/shape` rewrites a user's raw answer for a field into the artifact's formal language (grounded in the field's guidance and fund/artifact context), and `POST /artifacts/{id}/assist/coherence` returns a clarity/consistency assessment of the assembled artifact. OpenAI (`gpt-4o-mini` by default) is the active provider, read from `OPENAI_API_KEY`; the endpoints degrade to 503 when the LLM is unconfigured or unavailable, leaving all drafting/CRUD intact. Tests use deterministic doubles — no API spend in CI.

## Notes carried forward

- **Phase 4:** AI SDG-target suggestion (from the loaded 169-target framework) and GA-resolution web search — both attach as additional assist endpoints using the same `LLMProvider` interface.
- **Structured coherence output:** v1 returns free-text. A later iteration can request JSON (issues with section/field anchors) for richer UI, with tolerant parsing.
- **Full guideline grounding:** v1 grounds on the schema's per-field `guidance`. Parsing the full `docs/guidelines/*.docx` into retrievable context is a later enhancement.
- **Streaming + token/cost controls:** per-call token caps exist; streaming responses and usage accounting are future work.
- **Deployment:** `openai` is added to `backend/requirements.txt`, and `CIDY_DEV_MODE`/`OPENAI_API_KEY`/`CIDY_LLM_MODEL` must be set in the Lambda environment (Phase 2C/2C-deploy notes) for the assist endpoints to work in a deployed environment.
