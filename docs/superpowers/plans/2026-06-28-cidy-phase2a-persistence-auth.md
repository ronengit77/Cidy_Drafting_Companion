# CIdy Phase 2A — Persistence + Auth Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up CIdy's backend service skeleton with a PostgreSQL data layer and passwordless magic-link authentication, so later phases can attach artifact CRUD on an authenticated, persisted foundation.

**Architecture:** A FastAPI application (`cidy_api`) that runs locally as a normal ASGI app and deploys to AWS Lambda via Mangum (Mangum/SAM land in Phase 2B). Persistence uses SQLAlchemy 2.0 (sync) over PostgreSQL with `psycopg` v3; schema changes are managed by Alembic. Auth is passwordless: a single-use, hashed, short-TTL magic-link token is exchanged for a short-lived JWT session. Email sending is abstracted behind a sink that, in dev, logs/returns the link instead of sending.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync) + psycopg v3, Alembic, PyJWT, pydantic-settings, Pydantic v2, pytest + Starlette TestClient (httpx), Docker Compose Postgres.

## Global Constraints

- Python version floor: **3.12**.
- Database access is **SQLAlchemy 2.0 sync** style (`Mapped`/`mapped_column`, `Session`); driver is `psycopg` v3 (`postgresql+psycopg://`). No SQLAlchemy 1.x patterns.
- Pydantic v2 and **pydantic-settings** for config. No Pydantic v1 calls.
- All new service code lives under `backend/cidy_api/`. Tests under `backend/tests/api/`. The Phase 1 `cidy` package is a dependency and MUST NOT be modified by this phase.
- Settings come from environment variables with prefix **`CIDY_`** (e.g. `CIDY_DATABASE_URL`, `CIDY_JWT_SECRET`). Dev-safe defaults are provided so tests run with only a Postgres instance available.
- Magic-link tokens are stored **hashed** (SHA-256), are **single-use** (consumed on verify), and expire (default 15 minutes). JWTs are HS256, default 60-minute expiry.
- Tests require a running Postgres (provided by `docker-compose.yml`). Tests isolate via per-test transaction rollback; they must not depend on test execution order.
- Commit after every task with a `feat:`/`test:`/`chore:` prefixed message, staging specific files (never `git add -A`).

## Prerequisites

This phase builds on the Phase 1 `cidy` library. Execute it on a branch that **contains Phase 1** (branch from `master` after PR #1 merges, or branch from `phase1-core-domain`). Before Task 1, confirm `cd backend && python -c "import cidy; print(cidy.__version__)"` prints `0.1.0`.

## File Structure (created across this plan)

```
backend/
  cidy_api/
    __init__.py
    config.py            # Settings (pydantic-settings), env prefix CIDY_
    db.py                # SQLAlchemy engine, SessionLocal, Base, get_session
    models_db.py         # ORM models: User, AuthToken
    auth.py              # token generation/hashing/verify, JWT encode/decode
    dto.py               # Pydantic request/response models for auth
    deps.py              # FastAPI deps: get_db, get_current_user
    email_sink.py        # send_magic_link abstraction (dev = log/return)
    repositories/
      __init__.py
      users.py           # get_or_create_by_email, touch_last_login
      auth_tokens.py     # create_token, consume_token
    routers/
      __init__.py
      auth.py            # POST /auth/magic-link, POST /auth/verify
      me.py              # GET /me (protected smoke endpoint)
    app.py               # create_app(): FastAPI factory wiring routers + health
  alembic/
    env.py
    versions/0001_initial.py
  alembic.ini
  tests/api/
    __init__.py
    conftest.py          # db engine/session fixtures + TestClient
    test_health.py
    test_db.py
    test_models.py
    test_auth_core.py
    test_auth_router.py
    test_me.py
docker-compose.yml       # local Postgres
```

---

### Task 1: Service scaffolding, config, and health endpoint

**Files:**
- Modify: `backend/pyproject.toml` (add API dependencies)
- Create: `backend/cidy_api/__init__.py`
- Create: `backend/cidy_api/config.py`
- Create: `backend/cidy_api/app.py`
- Create: `docker-compose.yml` (repo root)
- Create: `backend/tests/api/__init__.py`
- Create: `backend/tests/api/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `cidy_api.config.Settings` (pydantic-settings `BaseSettings`, env prefix `CIDY_`) with fields: `database_url: str` (default `postgresql+psycopg://cidy:cidy@localhost:5432/cidy`), `jwt_secret: str` (default `"dev-secret-change-me"`), `jwt_algorithm: str = "HS256"`, `jwt_expire_minutes: int = 60`, `magic_link_expire_minutes: int = 15`, `app_base_url: str = "http://localhost:8000"`, `dev_mode: bool = True`.
  - `cidy_api.config.get_settings() -> Settings` (cached).
  - `cidy_api.app.create_app() -> FastAPI` exposing `GET /health` → `{"status": "ok"}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/__init__.py`:
```python
```

`backend/tests/api/test_health.py`:
```python
from fastapi.testclient import TestClient

from cidy_api.app import create_app


def test_health_ok():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api'` (or `fastapi`).

- [ ] **Step 3: Add dependencies and implement**

In `backend/pyproject.toml`, replace the `dependencies` and `optional-dependencies` blocks with:
```toml
dependencies = [
  "pydantic>=2.6,<3",
  "fastapi>=0.110,<1",
  "pydantic-settings>=2.2,<3",
  "sqlalchemy>=2.0,<3",
  "psycopg[binary]>=3.1,<4",
  "alembic>=1.13,<2",
  "pyjwt>=2.8,<3",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27", "uvicorn>=0.29"]
```

`backend/cidy_api/__init__.py`:
```python
```

`backend/cidy_api/config.py`:
```python
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIDY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://cidy:cidy@localhost:5432/cidy"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    magic_link_expire_minutes: int = 15
    app_base_url: str = "http://localhost:8000"
    dev_mode: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/cidy_api/app.py`:
```python
from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="CIdy Drafting Companion API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

`docker-compose.yml` (repo root):
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: cidy
      POSTGRES_PASSWORD: cidy
      POSTGRES_DB: cidy
    ports:
      - "5432:5432"
    volumes:
      - cidy_pgdata:/var/lib/postgresql/data

volumes:
  cidy_pgdata:
```

- [ ] **Step 4: Install deps and run the test**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/api/test_health.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/cidy_api/__init__.py backend/cidy_api/config.py backend/cidy_api/app.py docker-compose.yml backend/tests/api/__init__.py backend/tests/api/test_health.py
git commit -m "chore: scaffold cidy_api service with config and health endpoint"
```

---

### Task 2: Database engine, session, and test fixtures

**Files:**
- Create: `backend/cidy_api/db.py`
- Create: `backend/tests/api/conftest.py`
- Create: `backend/tests/api/test_db.py`

**Interfaces:**
- Consumes: `get_settings` (Task 1).
- Produces:
  - `cidy_api.db.Base` — SQLAlchemy 2.0 `DeclarativeBase` subclass (shared metadata for all ORM models).
  - `cidy_api.db.engine` — module-level `Engine` built from `get_settings().database_url`.
  - `cidy_api.db.SessionLocal` — `sessionmaker[Session]` bound to `engine`.
  - `cidy_api.db.get_session() -> Iterator[Session]` — generator yielding a session and closing it (used as the FastAPI DB dependency).
  - Test fixtures in `conftest.py`: `db_session` (function-scoped `Session` wrapped in a rolled-back transaction) and `client` (TestClient with `get_session` overridden to use `db_session`).

**Context:** Tasks 3+ define ORM models on `Base`. The `conftest` creates all tables once per session via `Base.metadata.create_all` and isolates each test in a transaction that is rolled back, so tests never see each other's writes and require no row cleanup.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_db.py`:
```python
from sqlalchemy import text


def test_db_session_executes(db_session):
    result = db_session.execute(text("SELECT 1")).scalar_one()
    assert result == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_db.py -v`
Expected: FAIL — fixture `db_session` not found (conftest/db not created yet).

- [ ] **Step 3: Implement db module and fixtures**

`backend/cidy_api/db.py`:
```python
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from cidy_api.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

`backend/tests/api/conftest.py`:
```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import cidy_api.models_db  # noqa: F401  (registers all ORM models on Base.metadata)
from cidy_api.app import create_app
from cidy_api.db import Base, engine, get_session


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

NOTE: `conftest.py` imports `cidy_api.models_db`, created in Task 3. Until Task 3 exists this import fails — that is expected; this task's `test_db` will pass only after Task 3 adds `models_db`. To keep Task 2 independently runnable, create a minimal placeholder now and let Task 3 replace it:

`backend/cidy_api/models_db.py` (placeholder for Task 2; Task 3 overwrites):
```python
from __future__ import annotations

# Models are added in Task 3. This module exists so conftest can import it.
```

- [ ] **Step 4: Start Postgres and run the test**

Run:
```bash
docker compose up -d db
cd backend && python -m pytest tests/api/test_db.py -v
```
Expected: PASS. (If Postgres isn't reachable, the failure message will be a connection error — start the container first.)

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/db.py backend/cidy_api/models_db.py backend/tests/api/conftest.py backend/tests/api/test_db.py
git commit -m "feat: add database engine, session, and test fixtures"
```

---

### Task 3: ORM models (User, AuthToken) and Alembic migration

**Files:**
- Modify: `backend/cidy_api/models_db.py` (replace placeholder)
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`
- Create: `backend/tests/api/test_models.py`

**Interfaces:**
- Consumes: `Base` (Task 2).
- Produces:
  - `cidy_api.models_db.User` — columns: `id: Mapped[uuid.UUID]` (pk, default `uuid4`), `email: Mapped[str]` (unique, not null), `created_at: Mapped[datetime]` (default now, tz-aware UTC), `last_login_at: Mapped[datetime | None]`.
  - `cidy_api.models_db.AuthToken` — columns: `id: Mapped[uuid.UUID]` (pk, default `uuid4`), `user_id: Mapped[uuid.UUID]` (FK `users.id`, not null), `token_hash: Mapped[str]` (not null, indexed), `expires_at: Mapped[datetime]` (not null), `consumed_at: Mapped[datetime | None]`, `created_at: Mapped[datetime]` (default now).
  - Alembic migration `0001_initial` creating both tables.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_models.py`:
```python
import uuid
from datetime import datetime, timedelta, timezone

from cidy_api.models_db import AuthToken, User


def test_create_user_and_token(db_session):
    user = User(email="a@example.com")
    db_session.add(user)
    db_session.flush()
    assert isinstance(user.id, uuid.UUID)
    assert user.created_at.tzinfo is not None

    token = AuthToken(
        user_id=user.id,
        token_hash="deadbeef",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db_session.add(token)
    db_session.flush()

    loaded = db_session.get(User, user.id)
    assert loaded.email == "a@example.com"
    assert db_session.get(AuthToken, token.id).consumed_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'User' from 'cidy_api.models_db'`.

- [ ] **Step 3: Implement models and Alembic migration**

`backend/cidy_api/models_db.py`:
```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from cidy_api.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
```

`backend/alembic.ini`:
```ini
[alembic]
script_location = alembic
prepend_sys_path = .

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

`backend/alembic/env.py`:
```python
from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

import cidy_api.models_db  # noqa: F401  (registers models)
from cidy_api.config import get_settings
from cidy_api.db import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

`backend/alembic/versions/0001_initial.py`:
```python
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_auth_tokens_token_hash", table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 4: Run the test and verify the migration applies**

Run: `cd backend && python -m pytest tests/api/test_models.py -v`
Expected: PASS (tables created via `conftest`'s `create_all`).

Also verify Alembic works against a fresh DB (manual, infra confidence check):
```bash
cd backend && alembic downgrade base && alembic upgrade head
```
Expected: completes without error; `alembic current` shows `0001_initial`.

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/models_db.py backend/alembic.ini backend/alembic backend/tests/api/test_models.py
git commit -m "feat: add User and AuthToken models with initial migration"
```

---

### Task 4: User and auth-token repositories

**Files:**
- Create: `backend/cidy_api/repositories/__init__.py`
- Create: `backend/cidy_api/repositories/users.py`
- Create: `backend/cidy_api/repositories/auth_tokens.py`
- Create: `backend/tests/api/test_repositories.py`

**Interfaces:**
- Consumes: `User`, `AuthToken` (Task 3).
- Produces:
  - `repositories.users.get_or_create_by_email(session, email: str) -> User` — normalizes email to lowercase/stripped; returns existing or newly-added user (flushed).
  - `repositories.users.touch_last_login(session, user: User) -> None` — sets `last_login_at = now(UTC)`.
  - `repositories.auth_tokens.create_token(session, user_id, token_hash, expires_at) -> AuthToken` — inserts and flushes.
  - `repositories.auth_tokens.consume_token(session, token_hash: str) -> AuthToken | None` — returns the matching token only if it exists, is unconsumed, and unexpired; marks it consumed (sets `consumed_at`) and flushes. Returns `None` otherwise.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_repositories.py`:
```python
from datetime import datetime, timedelta, timezone

from cidy_api.repositories import auth_tokens, users


def test_get_or_create_is_idempotent_and_normalizes(db_session):
    u1 = users.get_or_create_by_email(db_session, "  Bob@Example.com ")
    u2 = users.get_or_create_by_email(db_session, "bob@example.com")
    assert u1.id == u2.id
    assert u1.email == "bob@example.com"


def test_touch_last_login(db_session):
    u = users.get_or_create_by_email(db_session, "c@example.com")
    assert u.last_login_at is None
    users.touch_last_login(db_session, u)
    assert u.last_login_at is not None


def test_consume_token_happy_path(db_session):
    u = users.get_or_create_by_email(db_session, "d@example.com")
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    auth_tokens.create_token(db_session, u.id, "hash-1", exp)

    consumed = auth_tokens.consume_token(db_session, "hash-1")
    assert consumed is not None
    assert consumed.consumed_at is not None
    # second use fails (single-use)
    assert auth_tokens.consume_token(db_session, "hash-1") is None


def test_consume_token_rejects_expired(db_session):
    u = users.get_or_create_by_email(db_session, "e@example.com")
    exp = datetime.now(timezone.utc) - timedelta(minutes=1)
    auth_tokens.create_token(db_session, u.id, "hash-2", exp)
    assert auth_tokens.consume_token(db_session, "hash-2") is None


def test_consume_token_unknown_hash(db_session):
    assert auth_tokens.consume_token(db_session, "nope") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_repositories.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.repositories'`.

- [ ] **Step 3: Implement repositories**

`backend/cidy_api/repositories/__init__.py`:
```python
```

`backend/cidy_api/repositories/users.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from cidy_api.models_db import User


def _normalize(email: str) -> str:
    return email.strip().lower()


def get_or_create_by_email(session: Session, email: str) -> User:
    normalized = _normalize(email)
    existing = session.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if existing is not None:
        return existing
    user = User(email=normalized)
    session.add(user)
    session.flush()
    return user


def touch_last_login(session: Session, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    session.flush()
```

`backend/cidy_api/repositories/auth_tokens.py`:
```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from cidy_api.models_db import AuthToken


def create_token(
    session: Session, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> AuthToken:
    token = AuthToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    session.flush()
    return token


def consume_token(session: Session, token_hash: str) -> AuthToken | None:
    token = session.execute(
        select(AuthToken).where(AuthToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if token is None or token.consumed_at is not None:
        return None
    if token.expires_at <= datetime.now(timezone.utc):
        return None
    token.consumed_at = datetime.now(timezone.utc)
    session.flush()
    return token
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_repositories.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/repositories backend/tests/api/test_repositories.py
git commit -m "feat: add user and auth-token repositories"
```

---

### Task 5: Auth core (token + JWT primitives)

**Files:**
- Create: `backend/cidy_api/auth.py`
- Create: `backend/tests/api/test_auth_core.py`

**Interfaces:**
- Consumes: `get_settings` (Task 1).
- Produces (pure functions, no DB):
  - `auth.generate_magic_token() -> tuple[str, str]` — returns `(raw_token, token_hash)` where `raw_token = secrets.token_urlsafe(32)` and `token_hash = sha256(raw_token)` hexdigest.
  - `auth.hash_token(raw_token: str) -> str` — sha256 hexdigest (so verify can re-hash an incoming raw token).
  - `auth.create_jwt(user_id: uuid.UUID, *, now: datetime | None = None) -> str` — HS256 JWT with claims `sub` (str user id), `iat`, `exp` (now + `jwt_expire_minutes`).
  - `auth.decode_jwt(token: str) -> uuid.UUID` — verifies signature/exp and returns the `sub` as a UUID; raises `auth.AuthError` on any failure (bad signature, expired, malformed).
  - `auth.AuthError(Exception)`.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_auth_core.py`:
```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from cidy_api import auth


def test_generate_and_hash_consistency():
    raw, hashed = auth.generate_magic_token()
    assert auth.hash_token(raw) == hashed
    assert len(hashed) == 64  # sha256 hexdigest


def test_jwt_round_trip():
    uid = uuid.uuid4()
    token = auth.create_jwt(uid)
    assert auth.decode_jwt(token) == uid


def test_jwt_expired_rejected():
    uid = uuid.uuid4()
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token = auth.create_jwt(uid, now=past)
    with pytest.raises(auth.AuthError):
        auth.decode_jwt(token)


def test_jwt_tampered_rejected():
    with pytest.raises(auth.AuthError):
        auth.decode_jwt("not.a.jwt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_auth_core.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.auth'`.

- [ ] **Step 3: Implement auth core**

`backend/cidy_api/auth.py`:
```python
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from cidy_api.config import get_settings


class AuthError(Exception):
    """Raised when a token or JWT is invalid, expired, or malformed."""


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_magic_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def create_jwt(user_id: uuid.UUID, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthError(str(exc)) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_auth_core.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/auth.py backend/tests/api/test_auth_core.py
git commit -m "feat: add magic-token and JWT auth primitives"
```

---

### Task 6: Email sink and auth router

**Files:**
- Create: `backend/cidy_api/email_sink.py`
- Create: `backend/cidy_api/dto.py`
- Create: `backend/cidy_api/routers/__init__.py`
- Create: `backend/cidy_api/routers/auth.py`
- Modify: `backend/cidy_api/app.py` (include the auth router)
- Create: `backend/tests/api/test_auth_router.py`

**Interfaces:**
- Consumes: `get_session` (Task 2), `get_settings` (Task 1), `users`/`auth_tokens` repositories (Task 4), `auth` core (Task 5).
- Produces:
  - `email_sink.send_magic_link(email: str, link: str) -> None` — in `dev_mode`, logs the link (via `logging`); otherwise a `NotImplementedError` placeholder for the Phase 2B SES integration.
  - `dto.MagicLinkRequest` (`email: EmailStr`), `dto.MagicLinkResponse` (`sent: bool`, `dev_link: str | None`), `dto.VerifyRequest` (`token: str`), `dto.TokenResponse` (`access_token: str`, `token_type: str = "bearer"`).
  - Router routes on `app`:
    - `POST /auth/magic-link` → creates user (get-or-create), generates token, stores hash with expiry, builds link `"{app_base_url}/auth/verify?token={raw}"`, calls `send_magic_link`. Returns `MagicLinkResponse(sent=True, dev_link=<link if dev_mode else None>)`. Always returns 200 (no user enumeration).
    - `POST /auth/verify` → hashes the raw token, consumes it; on success updates `last_login`, returns `TokenResponse` with a fresh JWT; on failure returns 401.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_auth_router.py`:
```python
from cidy_api import auth


def test_magic_link_returns_dev_link(client):
    resp = client.post("/auth/magic-link", json={"email": "user@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert body["dev_link"] and "token=" in body["dev_link"]


def test_full_login_flow(client):
    resp = client.post("/auth/magic-link", json={"email": "flow@example.com"})
    dev_link = resp.json()["dev_link"]
    raw_token = dev_link.split("token=", 1)[1]

    verify = client.post("/auth/verify", json={"token": raw_token})
    assert verify.status_code == 200
    access = verify.json()["access_token"]
    # JWT decodes to a real user id
    assert auth.decode_jwt(access)


def test_verify_rejects_bad_token(client):
    resp = client.post("/auth/verify", json={"token": "garbage"})
    assert resp.status_code == 401


def test_verify_is_single_use(client):
    dev_link = client.post("/auth/magic-link", json={"email": "once@example.com"}).json()["dev_link"]
    raw_token = dev_link.split("token=", 1)[1]
    assert client.post("/auth/verify", json={"token": raw_token}).status_code == 200
    assert client.post("/auth/verify", json={"token": raw_token}).status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_auth_router.py -v`
Expected: FAIL — 404 on `/auth/magic-link` (router not wired) or import error.

- [ ] **Step 3: Implement email sink, DTOs, router, and wire it**

`backend/cidy_api/email_sink.py`:
```python
from __future__ import annotations

import logging

from cidy_api.config import get_settings

logger = logging.getLogger("cidy_api.email")


def send_magic_link(email: str, link: str) -> None:
    if get_settings().dev_mode:
        logger.info("DEV magic link for %s: %s", email, link)
        return
    raise NotImplementedError("SES email delivery is implemented in Phase 2B")
```

`backend/cidy_api/dto.py`:
```python
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    sent: bool
    dev_link: str | None = None


class VerifyRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

`backend/cidy_api/routers/__init__.py`:
```python
```

`backend/cidy_api/routers/auth.py`:
```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api import auth, email_sink
from cidy_api.config import get_settings
from cidy_api.db import get_session
from cidy_api.dto import MagicLinkRequest, MagicLinkResponse, TokenResponse, VerifyRequest
from cidy_api.models_db import User
from cidy_api.repositories import auth_tokens, users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-link", response_model=MagicLinkResponse)
def request_magic_link(payload: MagicLinkRequest, session: Session = Depends(get_session)) -> MagicLinkResponse:
    settings = get_settings()
    user = users.get_or_create_by_email(session, payload.email)
    raw, token_hash = auth.generate_magic_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expire_minutes)
    auth_tokens.create_token(session, user.id, token_hash, expires_at)
    link = f"{settings.app_base_url}/auth/verify?token={raw}"
    email_sink.send_magic_link(user.email, link)
    session.commit()
    return MagicLinkResponse(sent=True, dev_link=link if settings.dev_mode else None)


@router.post("/verify", response_model=TokenResponse)
def verify(payload: VerifyRequest, session: Session = Depends(get_session)) -> TokenResponse:
    token = auth_tokens.consume_token(session, auth.hash_token(payload.token))
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    user = session.get(User, token.user_id)
    users.touch_last_login(session, user)
    access = auth.create_jwt(user.id)
    session.commit()
    return TokenResponse(access_token=access)
```

`backend/cidy_api/app.py` (replace the file):
```python
from __future__ import annotations

from fastapi import FastAPI

from cidy_api.routers import auth as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="CIdy Drafting Companion API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router.router)
    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_auth_router.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/email_sink.py backend/cidy_api/dto.py backend/cidy_api/routers backend/cidy_api/app.py backend/tests/api/test_auth_router.py
git commit -m "feat: add magic-link request and verify endpoints"
```

---

### Task 7: Current-user dependency and protected /me endpoint

**Files:**
- Create: `backend/cidy_api/deps.py`
- Create: `backend/cidy_api/routers/me.py`
- Modify: `backend/cidy_api/app.py` (include the me router)
- Create: `backend/tests/api/test_me.py`

**Interfaces:**
- Consumes: `get_session` (Task 2), `auth.decode_jwt`/`AuthError` (Task 5), `User` (Task 3).
- Produces:
  - `deps.get_current_user(authorization: str | None, session) -> User` — FastAPI dependency that reads the `Authorization: Bearer <jwt>` header, decodes it, loads the `User`, and raises 401 on any failure (missing header, bad scheme, invalid JWT, unknown user).
  - `dto.UserResponse` (`id: uuid.UUID`, `email: str`) — add to `dto.py`.
  - Route `GET /me` → returns the authenticated user's `UserResponse`; 401 without a valid token.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_me.py`:
```python
def _login(client, email):
    dev_link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = dev_link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def test_me_requires_auth(client):
    assert client.get("/me").status_code == 401


def test_me_rejects_bad_token(client):
    resp = client.get("/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    access = _login(client, "me@example.com")
    resp = client.get("/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_me.py -v`
Expected: FAIL — 404 on `/me`.

- [ ] **Step 3: Implement dependency, DTO, and route**

Append to `backend/cidy_api/dto.py`:
```python
import uuid


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
```

`backend/cidy_api/deps.py`:
```python
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api.auth import AuthError, decode_jwt
from cidy_api.db import get_session
from cidy_api.models_db import User

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTH
    raw_jwt = authorization.split(" ", 1)[1]
    try:
        user_id = decode_jwt(raw_jwt)
    except AuthError:
        raise _UNAUTH
    user = session.get(User, user_id)
    if user is None:
        raise _UNAUTH
    return user
```

`backend/cidy_api/routers/me.py`:
```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from cidy_api.deps import get_current_user
from cidy_api.dto import UserResponse
from cidy_api.models_db import User

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
```

`backend/cidy_api/app.py` (replace the file):
```python
from __future__ import annotations

from fastapi import FastAPI

from cidy_api.routers import auth as auth_router
from cidy_api.routers import me as me_router


def create_app() -> FastAPI:
    app = FastAPI(title="CIdy Drafting Companion API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router.router)
    app.include_router(me_router.router)
    return app
```

- [ ] **Step 4: Run test and the full suite**

Run: `cd backend && python -m pytest tests/api/test_me.py -v && python -m pytest -q`
Expected: `test_me.py` PASS (3 tests); full suite (Phase 1 + Phase 2A) all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/cidy_api/deps.py backend/cidy_api/dto.py backend/cidy_api/routers/me.py backend/cidy_api/app.py backend/tests/api/test_me.py
git commit -m "feat: add current-user dependency and protected /me endpoint"
```

---

## Phase 2A completion

At the end of this plan the backend runs locally (`uvicorn cidy_api.app:create_app --factory`) against Docker Compose Postgres, with: environment-driven config, a migrated `users`/`auth_tokens` schema, user + token repositories, magic-link request/verify endpoints issuing JWT sessions, and a JWT-protected `/me` endpoint. This is the authenticated, persisted foundation that **Phase 2B** (schema registry, artifact repository with versioning + optimistic concurrency, artifacts/collaborators routers, validation/preview endpoint, and the Mangum handler + SAM template) builds on.

## Notes carried forward to Phase 2B

- Real email delivery (`email_sink.send_magic_link` non-dev path) via SES.
- The Mangum Lambda handler and SAM `template.yaml` (API Gateway, Lambda, RDS/Aurora, S3, SES) — deployment was intentionally deferred to keep 2A locally testable.
- Authorization (owner/collaborator/reviewer) helpers attach when artifacts exist.
- **Deploy config (security):** the SAM/Lambda environment MUST set `CIDY_DEV_MODE=false` and a strong `CIDY_JWT_SECRET` (≥32 bytes). `dev_mode` defaults to `True`, and `/auth/magic-link` returns the raw magic-link token (`dev_link`) while `dev_mode` is true — leaving it true in production would leak tokens. The config guard added in Phase 2A (commit `13c274a`) already refuses to boot with the dev/short JWT secret when `dev_mode=false`; the SAM template must wire both env vars.
