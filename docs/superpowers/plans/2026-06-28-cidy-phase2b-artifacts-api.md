# CIdy Phase 2B — Artifacts API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the artifact lifecycle API to the CIdy backend — fund/schema discovery, create/read/update/list of canonical artifacts with version history and optimistic-concurrency, shared (sequential) collaboration with owner/editor/reviewer authorization, and a validation/preview endpoint that reuses the Phase 1 engine.

**Architecture:** Builds on the Phase 2A `cidy_api` FastAPI service. Artifacts are stored in PostgreSQL with their canonical `values` in a `JSONB` column; every accepted edit snapshots the prior state into an `artifact_versions` table and bumps a `version_no` (optimistic-concurrency guard → HTTP 409). A filesystem-backed schema registry serves the Phase 1 Template Schemas and SDG framework. Authorization is enforced by a small `authz` helper (owner / editor / reviewer). The validation/preview endpoint reconstructs a Phase 1 canonical `Artifact` from stored content and runs `cidy.artifact.validation.validate_artifact`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync) + psycopg v3, Alembic, Pydantic v2, pytest + Starlette TestClient. Reuses the Phase 1 `cidy` library.

## Global Constraints

- Python version floor: **3.12**.
- SQLAlchemy 2.0 sync style (`Mapped`/`mapped_column`, `Session`); `JSONB` via `sqlalchemy.dialects.postgresql.JSONB`; psycopg v3. No SQLAlchemy 1.x patterns.
- All new service code under `backend/cidy_api/`; tests under `backend/tests/api/`. The Phase 1 `cidy` package and the existing Phase 2A `cidy_api` auth/db modules MUST NOT be modified except where a task explicitly says to extend a file (`models_db.py`, `dto.py`, `app.py`).
- Reuse Phase 1 via its public API only: `cidy.schema.loader.load_schema_file`, `cidy.reference.sdg.load_sdg_framework_file`, `cidy.artifact.models.Artifact` (the **canonical** artifact — import it aliased as `CanonicalArtifact` to avoid clashing with the DB `Artifact` model), `cidy.artifact.validation.validate_artifact`.
- The canonical artifact `values` are the nested dict from Phase 1; the DB stores exactly that nested dict in the `content` JSONB column.
- Authorization roles: an artifact has one **owner** (full control incl. managing collaborators); collaborators are **editor** (read + edit) or **reviewer** (read/export only). Editing is sequential (last-write-wins guarded by `version_no`); no real-time co-editing.
- Tests run against the **already-running** local Postgres (`postgresql://cidy:cidy@localhost:5432/cidy`) over TCP. Do **NOT** run `docker`/`docker compose` from the Bash shell (the Docker CLI fails there — a Windows named-pipe issue); the container is started separately. The `db_session`/`client` fixtures from Phase 2A (savepoint-isolated) are reused.
- TDD: failing test first, then implementation. Commit after each task with a `feat:`/`test:`/`chore:` prefixed message, staging specific files (never `git add -A`).

## Prerequisites

Execute on a branch containing Phase 1 + Phase 2A (this plan's branch `phase2b-artifacts-api` is cut from `master` after PR #2 merged). Before Task 1, confirm `cd backend && python -m pytest -q` is green (92 tests) and Postgres is reachable.

## File Structure (created/extended across this plan)

```
backend/cidy_api/
  schema_registry.py     # loads Phase 1 schemas + SDG framework; list/get (NEW)
  models_db.py           # + Artifact, ArtifactVersion, ArtifactCollaborator (EXTEND)
  authz.py               # access_level / require_artifact (NEW)
  dto.py                 # + artifact/collaborator/validation DTOs (EXTEND)
  repositories/
    artifacts.py         # CRUD + versioning + optimistic concurrency (NEW)
    collaborators.py     # add/remove/list/role (NEW)
  routers/
    schemas.py           # GET /schemas, /schemas/{id} (NEW)
    artifacts.py         # artifact endpoints (NEW)
    collaborators.py     # collaborator endpoints (NEW)
  app.py                 # include new routers (EXTEND)
  alembic/versions/0002_artifacts.py   # migration (NEW)
backend/tests/api/
  test_schema_registry.py, test_schemas_router.py,
  test_artifact_models.py, test_artifacts_repo.py, test_artifacts_versioning.py,
  test_authz.py, test_collaborators.py, test_artifacts_router.py, test_validation_endpoint.py
```

---

### Task 1: Schema registry and schema endpoints

**Files:**
- Create: `backend/cidy_api/schema_registry.py`
- Create: `backend/cidy_api/routers/schemas.py`
- Modify: `backend/cidy_api/app.py` (include the schemas router)
- Create: `backend/tests/api/test_schema_registry.py`
- Create: `backend/tests/api/test_schemas_router.py`

**Interfaces:**
- Consumes: Phase 1 `load_schema_file`, `load_sdg_framework_file`.
- Produces:
  - `schema_registry.SchemaInfo` (Pydantic): `schema_id: str`, `version: str`, `fund: str`, `artifact_type: str`, `title: str`.
  - `schema_registry.list_schemas() -> list[SchemaInfo]` — loads every `schemas/*.json` at repo root, cached.
  - `schema_registry.get_schema(schema_id: str) -> TemplateSchema | None` — returns the Phase 1 `TemplateSchema` for an id, or `None`.
  - `schema_registry.get_sdg_framework() -> SDGFramework` — cached load of `data/sdg_framework.json`.
  - Routes: `GET /schemas` → `list[SchemaInfo]`; `GET /schemas/{schema_id}` → the full schema JSON (200) or 404.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_schema_registry.py`:
```python
from cidy_api import schema_registry


def test_list_schemas_includes_da_and_rptc():
    infos = schema_registry.list_schemas()
    ids = {i.schema_id for i in infos}
    assert "da-concept-note" in ids
    assert "rptc-activity-proposal" in ids
    funds = {i.fund for i in infos}
    assert {"DA", "RPTC"} <= funds


def test_get_schema_returns_template_schema():
    schema = schema_registry.get_schema("rptc-activity-proposal")
    assert schema is not None
    assert schema.fund == "RPTC"
    assert any(s.id == "cover_sheet" for s in schema.sections)


def test_get_schema_unknown_is_none():
    assert schema_registry.get_schema("nope") is None


def test_get_sdg_framework_has_169_targets():
    fw = schema_registry.get_sdg_framework()
    assert len(fw.all_target_codes()) == 169
```

`backend/tests/api/test_schemas_router.py`:
```python
def test_list_schemas_endpoint(client):
    resp = client.get("/schemas")
    assert resp.status_code == 200
    ids = {row["schema_id"] for row in resp.json()}
    assert {"da-concept-note", "rptc-activity-proposal"} <= ids


def test_get_schema_endpoint(client):
    resp = client.get("/schemas/da-concept-note")
    assert resp.status_code == 200
    assert resp.json()["fund"] == "DA"


def test_get_unknown_schema_404(client):
    assert client.get("/schemas/nope").status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/api/test_schema_registry.py tests/api/test_schemas_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.schema_registry'` / 404 on `/schemas`.

- [ ] **Step 3: Implement the registry and router**

`backend/cidy_api/schema_registry.py`:
```python
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from cidy.reference.sdg import SDGFramework, load_sdg_framework_file
from cidy.schema.loader import load_schema_file
from cidy.schema.models import TemplateSchema

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_DIR = _REPO_ROOT / "schemas"
_SDG_PATH = _REPO_ROOT / "data" / "sdg_framework.json"


class SchemaInfo(BaseModel):
    schema_id: str
    version: str
    fund: str
    artifact_type: str
    title: str


@lru_cache
def _load_all() -> dict[str, TemplateSchema]:
    schemas: dict[str, TemplateSchema] = {}
    for path in sorted(_SCHEMAS_DIR.glob("*.json")):
        schema = load_schema_file(path)
        schemas[schema.schema_id] = schema
    return schemas


def list_schemas() -> list[SchemaInfo]:
    return [
        SchemaInfo(
            schema_id=s.schema_id,
            version=s.version,
            fund=s.fund,
            artifact_type=s.artifact_type,
            title=s.title,
        )
        for s in _load_all().values()
    ]


def get_schema(schema_id: str) -> TemplateSchema | None:
    return _load_all().get(schema_id)


@lru_cache
def get_sdg_framework() -> SDGFramework:
    return load_sdg_framework_file(_SDG_PATH)
```

`backend/cidy_api/routers/schemas.py`:
```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from cidy_api import schema_registry

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("", response_model=list[schema_registry.SchemaInfo])
def list_schemas() -> list[schema_registry.SchemaInfo]:
    return schema_registry.list_schemas()


@router.get("/{schema_id}")
def get_schema(schema_id: str) -> dict:
    schema = schema_registry.get_schema(schema_id)
    if schema is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown schema")
    return schema.model_dump()
```

In `backend/cidy_api/app.py`, add the import and include line (place with the other router includes):
```python
from cidy_api.routers import schemas as schemas_router
```
and inside `create_app`, after the existing `app.include_router(...)` calls:
```python
    app.include_router(schemas_router.router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/api/test_schema_registry.py tests/api/test_schemas_router.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/schema_registry.py backend/cidy_api/routers/schemas.py backend/cidy_api/app.py backend/tests/api/test_schema_registry.py backend/tests/api/test_schemas_router.py
git commit -m "feat: add schema registry and schema discovery endpoints"
```

---

### Task 2: Artifact ORM models and migration

**Files:**
- Modify: `backend/cidy_api/models_db.py` (add three models)
- Create: `backend/alembic/versions/0002_artifacts.py`
- Create: `backend/tests/api/test_artifact_models.py`

**Interfaces:**
- Consumes: `Base`, `User` (Phase 2A).
- Produces:
  - `models_db.Artifact`: `id: uuid` (pk, default uuid4), `owner_id: uuid` (FK users.id), `schema_id: str`, `schema_version: str`, `title: str` (default ""), `content: dict` (JSONB, default `{}`), `version_no: int` (default 1), `status: str` (default "draft"), `created_at`, `updated_at` (tz-aware; `updated_at` default now).
  - `models_db.ArtifactVersion`: `id: uuid` (pk), `artifact_id: uuid` (FK artifacts.id cascade), `version_no: int`, `title: str`, `content: dict` (JSONB), `author_id: uuid` (FK users.id), `created_at`.
  - `models_db.ArtifactCollaborator`: `id: uuid` (pk), `artifact_id: uuid` (FK artifacts.id cascade), `user_id: uuid` (FK users.id), `role: str` (`"editor"`/`"reviewer"`), `created_at`; unique on (`artifact_id`, `user_id`).
  - Alembic `0002_artifacts` (down_revision `0001_initial`) creating all three tables.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_artifact_models.py`:
```python
from cidy_api.models_db import Artifact, ArtifactCollaborator, ArtifactVersion, User
from cidy_api.repositories import users


def test_create_artifact_with_jsonb_content(db_session):
    owner = users.get_or_create_by_email(db_session, "owner@example.com")
    art = Artifact(
        owner_id=owner.id,
        schema_id="rptc-activity-proposal",
        schema_version="2024",
        title="Draft 1",
        content={"cover_sheet": {"proposed_budget": 50000}},
    )
    db_session.add(art)
    db_session.flush()
    assert art.version_no == 1
    assert art.status == "draft"
    loaded = db_session.get(Artifact, art.id)
    assert loaded.content["cover_sheet"]["proposed_budget"] == 50000


def test_version_and_collaborator_rows(db_session):
    owner = users.get_or_create_by_email(db_session, "o2@example.com")
    collab = users.get_or_create_by_email(db_session, "c2@example.com")
    art = Artifact(owner_id=owner.id, schema_id="s", schema_version="1")
    db_session.add(art)
    db_session.flush()
    db_session.add(ArtifactVersion(
        artifact_id=art.id, version_no=1, title="", content={}, author_id=owner.id
    ))
    db_session.add(ArtifactCollaborator(artifact_id=art.id, user_id=collab.id, role="editor"))
    db_session.flush()
    assert db_session.get(Artifact, art.id) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_artifact_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Artifact' from 'cidy_api.models_db'`.

- [ ] **Step 3: Add models and migration**

Append to `backend/cidy_api/models_db.py` (the file already imports `uuid`, `datetime`, `timezone`, `_utcnow`, `Base`, `Mapped`, `mapped_column`, `Uuid`, `String`, `DateTime`, `ForeignKey`; add `Integer` and the JSONB import):
```python
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import JSONB


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    schema_id: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ArtifactVersion(Base):
    __tablename__ = "artifact_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ArtifactCollaborator(Base):
    __tablename__ = "artifact_collaborators"
    __table_args__ = (UniqueConstraint("artifact_id", "user_id", name="uq_artifact_user"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
```
Also add `UniqueConstraint` to the existing top-of-file SQLAlchemy import line (e.g. `from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid`).

`backend/alembic/versions/0002_artifacts.py`:
```python
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_artifacts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("schema_id", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifacts_owner_id", "artifacts", ["owner_id"])
    op.create_table(
        "artifact_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_artifact_versions_artifact_id", "artifact_versions", ["artifact_id"])
    op.create_table(
        "artifact_collaborators",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.Uuid(), sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("artifact_id", "user_id", name="uq_artifact_user"),
    )
    op.create_index("ix_artifact_collaborators_artifact_id", "artifact_collaborators", ["artifact_id"])
    op.create_index("ix_artifact_collaborators_user_id", "artifact_collaborators", ["user_id"])


def downgrade() -> None:
    op.drop_table("artifact_collaborators")
    op.drop_index("ix_artifact_versions_artifact_id", table_name="artifact_versions")
    op.drop_table("artifact_versions")
    op.drop_index("ix_artifacts_owner_id", table_name="artifacts")
    op.drop_table("artifacts")
```

- [ ] **Step 4: Run test, verify migration**

Run: `cd backend && python -m pytest tests/api/test_artifact_models.py -v`
Expected: PASS (2 tests; tables created via `conftest`'s `create_all`).
Then verify migrations: `cd backend && python -m alembic downgrade base && python -m alembic upgrade head` — completes; `python -m alembic current` shows `0002_artifacts`.

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/models_db.py backend/alembic/versions/0002_artifacts.py backend/tests/api/test_artifact_models.py
git commit -m "feat: add Artifact, ArtifactVersion, ArtifactCollaborator models and migration"
```

---

### Task 3: Artifact repository — create, get, list

**Files:**
- Create: `backend/cidy_api/repositories/artifacts.py`
- Create: `backend/tests/api/test_artifacts_repo.py`

**Interfaces:**
- Consumes: `Artifact`, `ArtifactCollaborator` (Task 2).
- Produces:
  - `repositories.artifacts.create_artifact(session, *, owner_id, schema_id, schema_version, title, content) -> Artifact` — inserts (version_no=1) and flushes.
  - `repositories.artifacts.get_artifact(session, artifact_id) -> Artifact | None`.
  - `repositories.artifacts.list_for_user(session, user_id) -> list[Artifact]` — artifacts the user owns OR collaborates on, newest `updated_at` first.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_artifacts_repo.py`:
```python
from cidy_api.models_db import ArtifactCollaborator
from cidy_api.repositories import artifacts, users


def _mk(db_session, owner, title="t"):
    return artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1",
        title=title, content={"a": 1},
    )


def test_create_and_get(db_session):
    owner = users.get_or_create_by_email(db_session, "ro@example.com")
    art = _mk(db_session, owner)
    assert art.version_no == 1
    assert artifacts.get_artifact(db_session, art.id).content == {"a": 1}


def test_list_includes_owned_and_collaborated(db_session):
    owner = users.get_or_create_by_email(db_session, "ro2@example.com")
    other = users.get_or_create_by_email(db_session, "ro3@example.com")
    mine = _mk(db_session, owner, "mine")
    theirs = _mk(db_session, other, "theirs")
    db_session.add(ArtifactCollaborator(artifact_id=theirs.id, user_id=owner.id, role="editor"))
    db_session.flush()
    ids = {a.id for a in artifacts.list_for_user(db_session, owner.id)}
    assert mine.id in ids
    assert theirs.id in ids


def test_list_excludes_unrelated(db_session):
    owner = users.get_or_create_by_email(db_session, "ro4@example.com")
    stranger = users.get_or_create_by_email(db_session, "ro5@example.com")
    _mk(db_session, stranger, "not mine")
    assert artifacts.list_for_user(db_session, owner.id) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_artifacts_repo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.repositories.artifacts'`.

- [ ] **Step 3: Implement the repository**

`backend/cidy_api/repositories/artifacts.py`:
```python
from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cidy_api.models_db import Artifact, ArtifactCollaborator


def create_artifact(
    session: Session,
    *,
    owner_id: uuid.UUID,
    schema_id: str,
    schema_version: str,
    title: str,
    content: dict,
) -> Artifact:
    artifact = Artifact(
        owner_id=owner_id,
        schema_id=schema_id,
        schema_version=schema_version,
        title=title,
        content=content,
    )
    session.add(artifact)
    session.flush()
    return artifact


def get_artifact(session: Session, artifact_id: uuid.UUID) -> Artifact | None:
    return session.get(Artifact, artifact_id)


def list_for_user(session: Session, user_id: uuid.UUID) -> list[Artifact]:
    collab_ids = select(ArtifactCollaborator.artifact_id).where(
        ArtifactCollaborator.user_id == user_id
    )
    stmt = (
        select(Artifact)
        .where(or_(Artifact.owner_id == user_id, Artifact.id.in_(collab_ids)))
        .order_by(Artifact.updated_at.desc())
    )
    return list(session.execute(stmt).scalars().all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_artifacts_repo.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/repositories/artifacts.py backend/tests/api/test_artifacts_repo.py
git commit -m "feat: add artifact repository create/get/list"
```

---

### Task 4: Artifact repository — optimistic-concurrency update, versioning, restore

**Files:**
- Modify: `backend/cidy_api/repositories/artifacts.py`
- Create: `backend/tests/api/test_artifacts_versioning.py`

**Interfaces:**
- Consumes: `Artifact`, `ArtifactVersion` (Task 2); functions from Task 3.
- Produces (added to `repositories/artifacts.py`):
  - `repositories.artifacts.ConflictError(Exception)`.
  - `repositories.artifacts.VersionNotFound(Exception)`.
  - `update_artifact(session, artifact, *, expected_version_no, title, content, author_id) -> Artifact` — if `artifact.version_no != expected_version_no`, raise `ConflictError`. Otherwise snapshot the CURRENT state into `ArtifactVersion` (with the current `version_no`), then apply `title`/`content`, increment `version_no`, set `updated_at=now`, flush, return the artifact.
  - `list_versions(session, artifact_id) -> list[ArtifactVersion]` — newest `version_no` first.
  - `restore_version(session, artifact, target_version_no, *, author_id) -> Artifact` — if no `ArtifactVersion` with that `version_no`, raise `VersionNotFound`; otherwise snapshot current state, then set the artifact's `title`/`content` to the target version's, increment `version_no`, flush.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_artifacts_versioning.py`:
```python
import pytest

from cidy_api.repositories import artifacts, users


def _mk(db_session):
    owner = users.get_or_create_by_email(db_session, "ver@example.com")
    art = artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1",
        title="v1", content={"n": 1},
    )
    return owner, art


def test_update_bumps_version_and_snapshots(db_session):
    owner, art = _mk(db_session)
    updated = artifacts.update_artifact(
        db_session, art, expected_version_no=1, title="v2", content={"n": 2}, author_id=owner.id
    )
    assert updated.version_no == 2
    assert updated.content == {"n": 2}
    versions = artifacts.list_versions(db_session, art.id)
    assert len(versions) == 1
    assert versions[0].version_no == 1
    assert versions[0].content == {"n": 1}


def test_update_stale_version_conflicts(db_session):
    owner, art = _mk(db_session)
    artifacts.update_artifact(
        db_session, art, expected_version_no=1, title="v2", content={"n": 2}, author_id=owner.id
    )
    with pytest.raises(artifacts.ConflictError):
        artifacts.update_artifact(
            db_session, art, expected_version_no=1, title="x", content={"n": 9}, author_id=owner.id
        )


def test_restore_creates_new_version_from_old(db_session):
    owner, art = _mk(db_session)
    artifacts.update_artifact(
        db_session, art, expected_version_no=1, title="v2", content={"n": 2}, author_id=owner.id
    )
    restored = artifacts.restore_version(db_session, art, 1, author_id=owner.id)
    assert restored.version_no == 3
    assert restored.content == {"n": 1}  # back to v1 content


def test_restore_unknown_version_raises(db_session):
    owner, art = _mk(db_session)
    with pytest.raises(artifacts.VersionNotFound):
        artifacts.restore_version(db_session, art, 99, author_id=owner.id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_artifacts_versioning.py -v`
Expected: FAIL — `AttributeError: module 'cidy_api.repositories.artifacts' has no attribute 'update_artifact'`.

- [ ] **Step 3: Add update/versioning/restore**

Append to `backend/cidy_api/repositories/artifacts.py` (add imports `from datetime import datetime, timezone` and `from cidy_api.models_db import ArtifactVersion`):
```python
class ConflictError(Exception):
    """Raised when an update's expected version_no does not match current."""


class VersionNotFound(Exception):
    """Raised when restoring a version_no that has no snapshot."""


def _snapshot(session: Session, artifact: Artifact, author_id: uuid.UUID) -> None:
    session.add(
        ArtifactVersion(
            artifact_id=artifact.id,
            version_no=artifact.version_no,
            title=artifact.title,
            content=artifact.content,
            author_id=author_id,
        )
    )


def update_artifact(
    session: Session,
    artifact: Artifact,
    *,
    expected_version_no: int,
    title: str,
    content: dict,
    author_id: uuid.UUID,
) -> Artifact:
    if artifact.version_no != expected_version_no:
        raise ConflictError(
            f"expected version {expected_version_no}, current is {artifact.version_no}"
        )
    _snapshot(session, artifact, author_id)
    artifact.title = title
    artifact.content = content
    artifact.version_no += 1
    artifact.updated_at = datetime.now(timezone.utc)
    session.flush()
    return artifact


def list_versions(session: Session, artifact_id: uuid.UUID) -> list[ArtifactVersion]:
    stmt = (
        select(ArtifactVersion)
        .where(ArtifactVersion.artifact_id == artifact_id)
        .order_by(ArtifactVersion.version_no.desc())
    )
    return list(session.execute(stmt).scalars().all())


def restore_version(
    session: Session, artifact: Artifact, target_version_no: int, *, author_id: uuid.UUID
) -> Artifact:
    stmt = select(ArtifactVersion).where(
        ArtifactVersion.artifact_id == artifact.id,
        ArtifactVersion.version_no == target_version_no,
    )
    target = session.execute(stmt).scalar_one_or_none()
    if target is None:
        raise VersionNotFound(f"no version {target_version_no}")
    _snapshot(session, artifact, author_id)
    artifact.title = target.title
    artifact.content = target.content
    artifact.version_no += 1
    artifact.updated_at = datetime.now(timezone.utc)
    session.flush()
    return artifact
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_artifacts_versioning.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/repositories/artifacts.py backend/tests/api/test_artifacts_versioning.py
git commit -m "feat: add optimistic-concurrency update, versioning, and restore"
```

---

### Task 5: Authorization helper

**Files:**
- Create: `backend/cidy_api/authz.py`
- Create: `backend/tests/api/test_authz.py`

**Interfaces:**
- Consumes: `Artifact`, `ArtifactCollaborator`, `User` (Task 2); `get_artifact` (Task 3).
- Produces:
  - `authz.access_level(session, user, artifact) -> str | None` — `"owner"` if `artifact.owner_id == user.id`; else the collaborator `role` (`"editor"`/`"reviewer"`) if a row exists; else `None`.
  - `authz.require_artifact(session, user, artifact_id, need) -> Artifact` — loads the artifact (raises `HTTPException` 404 if missing); computes access level; raises `HTTPException` 403 if the level is insufficient for `need`. `need` ∈ `{"read", "edit", "own"}`. Read is satisfied by owner/editor/reviewer; edit by owner/editor; own by owner only.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_authz.py`:
```python
import uuid

import pytest
from fastapi import HTTPException

from cidy_api import authz
from cidy_api.models_db import ArtifactCollaborator
from cidy_api.repositories import artifacts, users


def _setup(db_session):
    owner = users.get_or_create_by_email(db_session, "ow@example.com")
    editor = users.get_or_create_by_email(db_session, "ed@example.com")
    reviewer = users.get_or_create_by_email(db_session, "rv@example.com")
    stranger = users.get_or_create_by_email(db_session, "st@example.com")
    art = artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1", title="t", content={}
    )
    db_session.add(ArtifactCollaborator(artifact_id=art.id, user_id=editor.id, role="editor"))
    db_session.add(ArtifactCollaborator(artifact_id=art.id, user_id=reviewer.id, role="reviewer"))
    db_session.flush()
    return owner, editor, reviewer, stranger, art


def test_access_levels(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    assert authz.access_level(db_session, owner, art) == "owner"
    assert authz.access_level(db_session, editor, art) == "editor"
    assert authz.access_level(db_session, reviewer, art) == "reviewer"
    assert authz.access_level(db_session, stranger, art) is None


def test_require_read_allows_all_members(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    for u in (owner, editor, reviewer):
        assert authz.require_artifact(db_session, u, art.id, "read").id == art.id
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, stranger, art.id, "read")
    assert exc.value.status_code == 403


def test_require_edit_excludes_reviewer(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    assert authz.require_artifact(db_session, editor, art.id, "edit").id == art.id
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, reviewer, art.id, "edit")
    assert exc.value.status_code == 403


def test_require_own_only_owner(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    assert authz.require_artifact(db_session, owner, art.id, "own").id == art.id
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, editor, art.id, "own")
    assert exc.value.status_code == 403


def test_require_missing_artifact_404(db_session):
    owner, *_ = _setup(db_session)
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, owner, uuid.uuid4(), "read")
    assert exc.value.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_authz.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.authz'`.

- [ ] **Step 3: Implement authz**

`backend/cidy_api/authz.py`:
```python
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from cidy_api.models_db import Artifact, ArtifactCollaborator, User

_READ = {"owner", "editor", "reviewer"}
_EDIT = {"owner", "editor"}
_OWN = {"owner"}
_NEEDS = {"read": _READ, "edit": _EDIT, "own": _OWN}


def access_level(session: Session, user: User, artifact: Artifact) -> str | None:
    if artifact.owner_id == user.id:
        return "owner"
    row = session.execute(
        select(ArtifactCollaborator.role).where(
            ArtifactCollaborator.artifact_id == artifact.id,
            ArtifactCollaborator.user_id == user.id,
        )
    ).scalar_one_or_none()
    return row


def require_artifact(
    session: Session, user: User, artifact_id: uuid.UUID, need: str
) -> Artifact:
    artifact = session.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    level = access_level(session, user, artifact)
    if level not in _NEEDS[need]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return artifact
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_authz.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/authz.py backend/tests/api/test_authz.py
git commit -m "feat: add artifact authorization helper"
```

---

### Task 6: Collaborators repository and endpoints

**Files:**
- Create: `backend/cidy_api/repositories/collaborators.py`
- Create: `backend/cidy_api/routers/collaborators.py`
- Modify: `backend/cidy_api/dto.py` (add collaborator DTOs)
- Modify: `backend/cidy_api/app.py` (include collaborators router)
- Create: `backend/tests/api/test_collaborators.py`

**Interfaces:**
- Consumes: `ArtifactCollaborator`, `User` (Task 2); `users.get_or_create_by_email` (Phase 2A); `authz.require_artifact` (Task 5); `get_current_user` (Phase 2A); `get_session` (Phase 2A).
- Produces:
  - `repositories.collaborators.add_collaborator(session, artifact_id, user_id, role) -> ArtifactCollaborator` — upserts role (updates if a row already exists for the pair).
  - `repositories.collaborators.remove_collaborator(session, artifact_id, user_id) -> bool` — deletes; returns whether a row was removed.
  - `repositories.collaborators.list_collaborators(session, artifact_id) -> list[ArtifactCollaborator]`.
  - `dto.CollaboratorAdd` (`email: EmailStr`, `role: Literal["editor","reviewer"]`), `dto.CollaboratorOut` (`user_id: uuid.UUID`, `email: str`, `role: str`).
  - Routes (all require auth; only the **owner** may manage collaborators):
    - `POST /artifacts/{artifact_id}/collaborators` → add/update (owner-only), 200 `CollaboratorOut`.
    - `DELETE /artifacts/{artifact_id}/collaborators/{user_id}` → 204 (owner-only); 404 if no such collaborator.
    - `GET /artifacts/{artifact_id}/collaborators` → `list[CollaboratorOut]` (any member can read).

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_collaborators.py`:
```python
def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _new_artifact(client, token):
    resp = client.post(
        "/artifacts",
        json={"schema_id": "rptc-activity-proposal", "title": "t"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_owner_adds_and_lists_collaborator(client):
    owner_t = _login(client, "co_owner@example.com")
    _login(client, "co_editor@example.com")  # ensure user exists
    art_id = _new_artifact(client, owner_t)

    add = client.post(
        f"/artifacts/{art_id}/collaborators",
        json={"email": "co_editor@example.com", "role": "editor"},
        headers=_auth(owner_t),
    )
    assert add.status_code == 200, add.text
    assert add.json()["role"] == "editor"

    listed = client.get(f"/artifacts/{art_id}/collaborators", headers=_auth(owner_t))
    assert listed.status_code == 200
    assert any(c["email"] == "co_editor@example.com" for c in listed.json())


def test_non_owner_cannot_add(client):
    owner_t = _login(client, "co_owner2@example.com")
    other_t = _login(client, "co_other@example.com")
    art_id = _new_artifact(client, owner_t)
    resp = client.post(
        f"/artifacts/{art_id}/collaborators",
        json={"email": "x@example.com", "role": "editor"},
        headers=_auth(other_t),
    )
    assert resp.status_code in (403, 404)


def test_remove_collaborator(client):
    owner_t = _login(client, "co_owner3@example.com")
    _login(client, "co_rm@example.com")
    art_id = _new_artifact(client, owner_t)
    client.post(
        f"/artifacts/{art_id}/collaborators",
        json={"email": "co_rm@example.com", "role": "reviewer"},
        headers=_auth(owner_t),
    )
    # fetch the collaborator's user_id from the list
    user_id = client.get(f"/artifacts/{art_id}/collaborators", headers=_auth(owner_t)).json()[0]["user_id"]
    rm = client.delete(f"/artifacts/{art_id}/collaborators/{user_id}", headers=_auth(owner_t))
    assert rm.status_code == 204
```

NOTE: this test depends on `POST /artifacts` (Task 7). Implement Task 7 BEFORE running this test green, OR run only the repository-level portion here. Because the router endpoints in this task and Task 7 are mutually dependent (both register under `/artifacts/...`), implement the collaborators repository + DTOs first, then the router, and run this file after Task 7's `POST /artifacts` exists. If executing strictly task-by-task, move the four endpoint tests' green-run to the end of Task 7 and keep only a repository unit test here.

To keep this task independently green, ALSO add this repository-level test which does not need the HTTP layer:
```python
from cidy_api.repositories import artifacts, collaborators, users


def test_add_update_remove_collaborator_repo(db_session):
    owner = users.get_or_create_by_email(db_session, "repo_owner@example.com")
    collab = users.get_or_create_by_email(db_session, "repo_collab@example.com")
    art = artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1", title="t", content={}
    )
    collaborators.add_collaborator(db_session, art.id, collab.id, "editor")
    rows = collaborators.list_collaborators(db_session, art.id)
    assert len(rows) == 1 and rows[0].role == "editor"
    collaborators.add_collaborator(db_session, art.id, collab.id, "reviewer")  # upsert
    assert collaborators.list_collaborators(db_session, art.id)[0].role == "reviewer"
    assert collaborators.remove_collaborator(db_session, art.id, collab.id) is True
    assert collaborators.list_collaborators(db_session, art.id) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_collaborators.py::test_add_update_remove_collaborator_repo -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.repositories.collaborators'`.

- [ ] **Step 3: Implement repository, DTOs, and router**

`backend/cidy_api/repositories/collaborators.py`:
```python
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cidy_api.models_db import ArtifactCollaborator


def add_collaborator(
    session: Session, artifact_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> ArtifactCollaborator:
    existing = session.execute(
        select(ArtifactCollaborator).where(
            ArtifactCollaborator.artifact_id == artifact_id,
            ArtifactCollaborator.user_id == user_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.role = role
        session.flush()
        return existing
    row = ArtifactCollaborator(artifact_id=artifact_id, user_id=user_id, role=role)
    session.add(row)
    session.flush()
    return row


def remove_collaborator(session: Session, artifact_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = session.execute(
        delete(ArtifactCollaborator).where(
            ArtifactCollaborator.artifact_id == artifact_id,
            ArtifactCollaborator.user_id == user_id,
        )
    )
    session.flush()
    return result.rowcount > 0


def list_collaborators(session: Session, artifact_id: uuid.UUID) -> list[ArtifactCollaborator]:
    return list(
        session.execute(
            select(ArtifactCollaborator).where(ArtifactCollaborator.artifact_id == artifact_id)
        ).scalars().all()
    )
```

Append to `backend/cidy_api/dto.py` (add `from typing import Literal` at top if absent):
```python
class CollaboratorAdd(BaseModel):
    email: EmailStr
    role: Literal["editor", "reviewer"]


class CollaboratorOut(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
```

`backend/cidy_api/routers/collaborators.py`:
```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from cidy_api import authz
from cidy_api.db import get_session
from cidy_api.deps import get_current_user
from cidy_api.dto import CollaboratorAdd, CollaboratorOut
from cidy_api.models_db import User
from cidy_api.repositories import collaborators, users

router = APIRouter(prefix="/artifacts/{artifact_id}/collaborators", tags=["collaborators"])


@router.post("", response_model=CollaboratorOut)
def add(
    artifact_id: uuid.UUID,
    payload: CollaboratorAdd,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CollaboratorOut:
    authz.require_artifact(session, current_user, artifact_id, "own")
    target = users.get_or_create_by_email(session, payload.email)
    row = collaborators.add_collaborator(session, artifact_id, target.id, payload.role)
    session.commit()
    return CollaboratorOut(user_id=target.id, email=target.email, role=row.role)


@router.get("", response_model=list[CollaboratorOut])
def list_(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CollaboratorOut]:
    authz.require_artifact(session, current_user, artifact_id, "read")
    out: list[CollaboratorOut] = []
    for row in collaborators.list_collaborators(session, artifact_id):
        user = session.get(User, row.user_id)
        out.append(CollaboratorOut(user_id=row.user_id, email=user.email, role=row.role))
    return out


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    artifact_id: uuid.UUID,
    user_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    authz.require_artifact(session, current_user, artifact_id, "own")
    removed = collaborators.remove_collaborator(session, artifact_id, user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collaborator not found")
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Wire into `backend/cidy_api/app.py`:
```python
from cidy_api.routers import collaborators as collaborators_router
```
and in `create_app`:
```python
    app.include_router(collaborators_router.router)
```

- [ ] **Step 4: Run repository test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_collaborators.py::test_add_update_remove_collaborator_repo -v`
Expected: PASS. (The HTTP endpoint tests in this file go green after Task 7 adds `POST /artifacts`.)

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/repositories/collaborators.py backend/cidy_api/routers/collaborators.py backend/cidy_api/dto.py backend/cidy_api/app.py backend/tests/api/test_collaborators.py
git commit -m "feat: add collaborators repository and management endpoints"
```

---

### Task 7: Artifacts router (CRUD, versions, restore)

**Files:**
- Create: `backend/cidy_api/routers/artifacts.py`
- Modify: `backend/cidy_api/dto.py` (add artifact DTOs)
- Modify: `backend/cidy_api/app.py` (include artifacts router)
- Create: `backend/tests/api/test_artifacts_router.py`

**Interfaces:**
- Consumes: `schema_registry.get_schema` (Task 1); `repositories.artifacts` (Tasks 3–4); `authz.require_artifact` (Task 5); `get_current_user`, `get_session` (Phase 2A).
- Produces:
  - `dto.ArtifactCreate` (`schema_id: str`, `title: str = ""`, `content: dict = {}`).
  - `dto.ArtifactUpdate` (`expected_version_no: int`, `title: str`, `content: dict`).
  - `dto.ArtifactSummary` (`id`, `schema_id`, `schema_version`, `title`, `version_no`, `status`, `updated_at`).
  - `dto.ArtifactDetail` (summary fields + `content: dict`, `owner_id`, `created_at`).
  - `dto.VersionSummary` (`version_no: int`, `title: str`, `created_at`).
  - Routes (all require auth):
    - `POST /artifacts` (201, `ArtifactDetail`) — body `ArtifactCreate`; rejects unknown `schema_id` with 400; sets `schema_version` from the registry; owner = current user.
    - `GET /artifacts` → `list[ArtifactSummary]` for the current user.
    - `GET /artifacts/{id}` → `ArtifactDetail` (read access).
    - `PUT /artifacts/{id}` → `ArtifactDetail` (edit access); body `ArtifactUpdate`; `ConflictError` → 409.
    - `GET /artifacts/{id}/versions` → `list[VersionSummary]` (read access).
    - `POST /artifacts/{id}/versions/{version_no}/restore` → `ArtifactDetail` (edit access); `VersionNotFound` → 404.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_artifacts_router.py`:
```python
def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_create_list_get(client):
    t = _login(client, "ar_owner@example.com")
    created = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "My draft"}, headers=_auth(t)
    )
    assert created.status_code == 201, created.text
    art = created.json()
    assert art["schema_version"] == "2024"
    assert art["version_no"] == 1

    listed = client.get("/artifacts", headers=_auth(t))
    assert any(a["id"] == art["id"] for a in listed.json())

    got = client.get(f"/artifacts/{art['id']}", headers=_auth(t))
    assert got.status_code == 200
    assert got.json()["title"] == "My draft"


def test_create_unknown_schema_400(client):
    t = _login(client, "ar_bad@example.com")
    resp = client.post("/artifacts", json={"schema_id": "nope", "title": "x"}, headers=_auth(t))
    assert resp.status_code == 400


def test_update_optimistic_conflict(client):
    t = _login(client, "ar_upd@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "v1"}, headers=_auth(t)
    ).json()
    ok = client.put(
        f"/artifacts/{art['id']}",
        json={"expected_version_no": 1, "title": "v2", "content": {"cover_sheet": {"proposed_budget": 1}}},
        headers=_auth(t),
    )
    assert ok.status_code == 200
    assert ok.json()["version_no"] == 2
    stale = client.put(
        f"/artifacts/{art['id']}",
        json={"expected_version_no": 1, "title": "v3", "content": {}},
        headers=_auth(t),
    )
    assert stale.status_code == 409


def test_versions_and_restore(client):
    t = _login(client, "ar_ver@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "v1"}, headers=_auth(t)
    ).json()
    client.put(
        f"/artifacts/{art['id']}",
        json={"expected_version_no": 1, "title": "v2", "content": {"x": 2}},
        headers=_auth(t),
    )
    versions = client.get(f"/artifacts/{art['id']}/versions", headers=_auth(t))
    assert versions.status_code == 200
    assert versions.json()[0]["version_no"] == 1
    restored = client.post(f"/artifacts/{art['id']}/versions/1/restore", headers=_auth(t))
    assert restored.status_code == 200
    assert restored.json()["version_no"] == 3


def test_get_requires_access(client):
    owner_t = _login(client, "ar_o@example.com")
    other_t = _login(client, "ar_x@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "p"}, headers=_auth(owner_t)
    ).json()
    assert client.get(f"/artifacts/{art['id']}", headers=_auth(other_t)).status_code in (403, 404)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_artifacts_router.py -v`
Expected: FAIL — 404 on `POST /artifacts` (router not present).

- [ ] **Step 3: Implement DTOs and router**

Append to `backend/cidy_api/dto.py`:
```python
from datetime import datetime


class ArtifactCreate(BaseModel):
    schema_id: str
    title: str = ""
    content: dict = {}


class ArtifactUpdate(BaseModel):
    expected_version_no: int
    title: str
    content: dict


class ArtifactSummary(BaseModel):
    id: uuid.UUID
    schema_id: str
    schema_version: str
    title: str
    version_no: int
    status: str
    updated_at: datetime


class ArtifactDetail(ArtifactSummary):
    owner_id: uuid.UUID
    content: dict
    created_at: datetime


class VersionSummary(BaseModel):
    version_no: int
    title: str
    created_at: datetime
```

`backend/cidy_api/routers/artifacts.py`:
```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api import authz, schema_registry
from cidy_api.db import get_session
from cidy_api.deps import get_current_user
from cidy_api.dto import (
    ArtifactCreate,
    ArtifactDetail,
    ArtifactSummary,
    ArtifactUpdate,
    VersionSummary,
)
from cidy_api.models_db import Artifact, User
from cidy_api.repositories import artifacts as artifacts_repo

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _detail(a: Artifact) -> ArtifactDetail:
    return ArtifactDetail(
        id=a.id, schema_id=a.schema_id, schema_version=a.schema_version, title=a.title,
        version_no=a.version_no, status=a.status, updated_at=a.updated_at,
        owner_id=a.owner_id, content=a.content, created_at=a.created_at,
    )


@router.post("", response_model=ArtifactDetail, status_code=status.HTTP_201_CREATED)
def create(
    payload: ArtifactCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    schema = schema_registry.get_schema(payload.schema_id)
    if schema is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown schema_id")
    artifact = artifacts_repo.create_artifact(
        session, owner_id=current_user.id, schema_id=schema.schema_id,
        schema_version=schema.version, title=payload.title, content=payload.content,
    )
    session.commit()
    return _detail(artifact)


@router.get("", response_model=list[ArtifactSummary])
def list_(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ArtifactSummary]:
    rows = artifacts_repo.list_for_user(session, current_user.id)
    return [
        ArtifactSummary(
            id=a.id, schema_id=a.schema_id, schema_version=a.schema_version, title=a.title,
            version_no=a.version_no, status=a.status, updated_at=a.updated_at,
        )
        for a in rows
    ]


@router.get("/{artifact_id}", response_model=ArtifactDetail)
def get(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = authz.require_artifact(session, current_user, artifact_id, "read")
    return _detail(artifact)


@router.put("/{artifact_id}", response_model=ArtifactDetail)
def update(
    artifact_id: uuid.UUID,
    payload: ArtifactUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = authz.require_artifact(session, current_user, artifact_id, "edit")
    try:
        artifacts_repo.update_artifact(
            session, artifact, expected_version_no=payload.expected_version_no,
            title=payload.title, content=payload.content, author_id=current_user.id,
        )
    except artifacts_repo.ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    session.commit()
    return _detail(artifact)


@router.get("/{artifact_id}/versions", response_model=list[VersionSummary])
def versions(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[VersionSummary]:
    authz.require_artifact(session, current_user, artifact_id, "read")
    return [
        VersionSummary(version_no=v.version_no, title=v.title, created_at=v.created_at)
        for v in artifacts_repo.list_versions(session, artifact_id)
    ]


@router.post("/{artifact_id}/versions/{version_no}/restore", response_model=ArtifactDetail)
def restore(
    artifact_id: uuid.UUID,
    version_no: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = authz.require_artifact(session, current_user, artifact_id, "edit")
    try:
        artifacts_repo.restore_version(session, artifact, version_no, author_id=current_user.id)
    except artifacts_repo.VersionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    session.commit()
    return _detail(artifact)
```

Wire into `backend/cidy_api/app.py`:
```python
from cidy_api.routers import artifacts as artifacts_router
```
and in `create_app` (include BEFORE the collaborators router is fine; order does not matter since paths differ):
```python
    app.include_router(artifacts_router.router)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/api/test_artifacts_router.py tests/api/test_collaborators.py -v`
Expected: PASS (Task 7's 5 tests AND the Task 6 HTTP collaborator tests that depend on `POST /artifacts`).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/routers/artifacts.py backend/cidy_api/dto.py backend/cidy_api/app.py backend/tests/api/test_artifacts_router.py
git commit -m "feat: add artifacts CRUD, versions, and restore endpoints"
```

---

### Task 8: Validation / preview endpoint

**Files:**
- Modify: `backend/cidy_api/routers/artifacts.py` (add the `/check` route)
- Modify: `backend/cidy_api/dto.py` (add validation DTOs)
- Create: `backend/tests/api/test_validation_endpoint.py`

**Interfaces:**
- Consumes: Phase 1 `cidy.artifact.models.Artifact` (aliased `CanonicalArtifact`), `cidy.artifact.validation.validate_artifact`; `schema_registry.get_schema`/`get_sdg_framework` (Task 1); `authz.require_artifact` (Task 5).
- Produces:
  - `dto.IssueOut` (`path: str`, `severity: str`, `message: str`).
  - `dto.ValidationReportOut` (`is_valid: bool`, `required_total: int`, `required_filled: int`, `missing: list[str]`, `issues: list[IssueOut]`).
  - Route: `POST /artifacts/{artifact_id}/check` → `ValidationReportOut` (read access) — loads the artifact, resolves its schema from the registry (500 if the schema is missing — data integrity), builds a `CanonicalArtifact(schema_id, schema_version, title, values=content)`, runs `validate_artifact`, and maps the report.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_validation_endpoint.py`:
```python
def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_check_reports_missing_required(client):
    t = _login(client, "val@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "p"}, headers=_auth(t)
    ).json()
    resp = client.post(f"/artifacts/{art['id']}/check", headers=_auth(t))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_valid"] is False  # empty content -> required fields missing
    assert body["required_total"] > 0
    assert any(m == "cover_sheet.brief_description" for m in body["missing"])


def test_check_requires_access(client):
    owner_t = _login(client, "val_o@example.com")
    other_t = _login(client, "val_x@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "p"}, headers=_auth(owner_t)
    ).json()
    assert client.post(f"/artifacts/{art['id']}/check", headers=_auth(other_t)).status_code in (403, 404)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_validation_endpoint.py -v`
Expected: FAIL — 404 on `/check`.

- [ ] **Step 3: Implement DTOs and the route**

Append to `backend/cidy_api/dto.py`:
```python
class IssueOut(BaseModel):
    path: str
    severity: str
    message: str


class ValidationReportOut(BaseModel):
    is_valid: bool
    required_total: int
    required_filled: int
    missing: list[str]
    issues: list[IssueOut]
```

Add to `backend/cidy_api/routers/artifacts.py` (add imports at top: `from cidy.artifact.models import Artifact as CanonicalArtifact`, `from cidy.artifact.validation import validate_artifact`, and extend the `cidy_api.dto` import to include `IssueOut, ValidationReportOut`):
```python
@router.post("/{artifact_id}/check", response_model=ValidationReportOut)
def check(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ValidationReportOut:
    artifact = authz.require_artifact(session, current_user, artifact_id, "read")
    schema = schema_registry.get_schema(artifact.schema_id)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="artifact references an unknown schema",
        )
    canonical = CanonicalArtifact(
        schema_id=artifact.schema_id,
        schema_version=artifact.schema_version,
        title=artifact.title,
        values=artifact.content,
        version_no=artifact.version_no,
    )
    report = validate_artifact(schema, canonical, schema_registry.get_sdg_framework())
    return ValidationReportOut(
        is_valid=report.is_valid,
        required_total=report.required_total,
        required_filled=report.required_filled,
        missing=report.missing,
        issues=[IssueOut(path=i.path, severity=i.severity, message=i.message) for i in report.issues],
    )
```

- [ ] **Step 4: Run the test and the full suite**

Run: `cd backend && python -m pytest tests/api/test_validation_endpoint.py -v && python -m pytest -q`
Expected: `test_validation_endpoint.py` PASS (2 tests); full suite (Phase 1 + 2A + 2B) all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/routers/artifacts.py backend/cidy_api/dto.py backend/tests/api/test_validation_endpoint.py
git commit -m "feat: add artifact validation/preview endpoint"
```

---

## Phase 2B completion

At the end of this plan the backend serves the full artifact lifecycle locally: discover funds/schemas (`GET /schemas`), create/list/read artifacts, edit with optimistic-concurrency + version history + restore, manage owner/editor/reviewer collaborators, and validate/preview an artifact via the Phase 1 engine — all authenticated (Phase 2A) and authorized, tested against real Postgres.

## Notes carried forward to Phase 2C (deployment) and later

- **Phase 2C (deploy):** Mangum Lambda handler, SAM `template.yaml` (API Gateway, Lambda, RDS/Aurora, S3, SES), SES email delivery, and the production env wiring (`CIDY_DEV_MODE=false`, strong `CIDY_JWT_SECRET`).
- Export/import (Word/PDF/JSON) is Phase 5; the `/check` endpoint and `content` JSONB are the inputs it will render from.
- LLM-assisted drafting, SDG suggestion, and GA-resolution search are Phases 3–4; they will read/write the same artifact `content`.
- `status` is currently always `"draft"`; a status-transition workflow can be added when submission/review states are needed.
- **Concurrency backstop (from 2B final review):** `update_artifact`/`restore_version` now take a `SELECT … FOR UPDATE` row lock (commit `bb59f37`) so concurrent edits correctly 409 instead of silently losing updates. As defense-in-depth, add a `UNIQUE(artifact_id, version_no)` constraint on `artifact_versions` (do it in a clean migration during 2C, since the dev DB schema is currently built via `create_all`).
- **Migration verification:** the test suite builds the schema via `Base.metadata.create_all`; add a CI/test step that runs `alembic upgrade head` against a pristine database, since production correctness depends on the migrations, not `create_all`.
