# CIdy Phase 2C — Deployment Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the CIdy backend deployable to AWS by producing — and validating locally, without provisioning any live resources — a Mangum Lambda adapter, an AWS SAM template, and a deploy runbook.

**Architecture:** The existing FastAPI app (`cidy_api.app.create_app`) is wrapped by Mangum so a single Lambda function serves the whole API behind an API Gateway HTTP API. A SAM `template.yaml` declares the Lambda, the HTTP API, and a PostgreSQL RDS instance. Per the chosen **dev posture**, the RDS instance is publicly reachable and the Lambda runs **outside a VPC** (simplest; documented as dev-only, not production-safe). Email (SES) is **not** wired in this phase — the app keeps its dev mock with an SES hook for later. Nothing here deploys: verification is `sam validate --lint`, a structural template test, and a synthetic-event test of the handler.

**Tech Stack:** Python 3.12, FastAPI, Mangum, AWS SAM (template + CLI), Pydantic v2, pytest. Reuses Phases 1/2A/2B.

## Global Constraints

- Python version floor: **3.12**; Lambda runtime target **python3.12**.
- This phase is **author + validate only** — it MUST NOT create live AWS resources (`sam deploy` is documented but never run here). Verification is `sam validate --lint`, a template-structure pytest, and the Mangum handler test.
- **Dev networking posture (deliberate):** the RDS instance is `PubliclyAccessible: true` with a security group open on 5432, and the Lambda is not in a VPC. This is dev-only and documented as such; production hardening (VPC, private RDS, RDS Proxy) is a later concern.
- SES is NOT integrated; the app's `email_sink` dev mock and the existing config guard stay as-is. Production env wiring (`CIDY_DEV_MODE=false`, strong `CIDY_JWT_SECRET`) is encoded in the template.
- The `sam` CLI is installed but only on the Windows/PowerShell PATH (not the Git Bash tool's PATH) — run `sam …` via the **PowerShell** tool. pytest runs in Git Bash as usual. Do NOT run `docker`/`docker compose` from Git Bash.
- New code under `backend/cidy_api/` and repo-root infra files (`template.yaml`, `samconfig.toml`, `DEPLOY.md`, `backend/requirements.txt`); tests under `backend/tests/api/`. Do NOT modify the Phase 1 `cidy` package or existing `cidy_api` modules except `pyproject.toml` (add the `mangum` dependency).
- TDD where testable; commit after each task with a `feat:`/`chore:` prefixed message, staging specific files (never `git add -A`).

## Prerequisites

On a branch containing Phases 1/2A/2B (`phase2c-deployment`, cut from `master` after PR #3). AWS credentials are configured (account 369560848350). Before Task 1, confirm `cd backend && python -m pytest -q` is green (124 tests).

## File Structure

```
backend/cidy_api/lambda_handler.py     # Mangum adapter (NEW)
backend/requirements.txt               # runtime deps for the Lambda build (NEW)
template.yaml                          # SAM template (NEW, repo root)
samconfig.toml                         # SAM deploy config (NEW, repo root)
DEPLOY.md                              # deploy runbook (NEW, repo root)
backend/tests/api/test_lambda_handler.py   # synthetic-event test (NEW)
backend/tests/api/test_sam_template.py     # template-structure test (NEW)
backend/tests/api/test_deploy_docs.py      # runbook content test (NEW)
backend/pyproject.toml                 # + mangum dependency (EDIT)
```

---

### Task 1: Mangum Lambda handler

**Files:**
- Modify: `backend/pyproject.toml` (add `mangum`)
- Create: `backend/cidy_api/lambda_handler.py`
- Create: `backend/tests/api/test_lambda_handler.py`

**Interfaces:**
- Consumes: `cidy_api.app.create_app` (Phase 2A).
- Produces: `cidy_api.lambda_handler.handler` — a `Mangum`-wrapped ASGI handler (`lifespan="off"`) callable as `handler(event, context)` with an API Gateway HTTP API (payload format 2.0) event.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_lambda_handler.py`:
```python
import json


def _http_event(method: str, path: str) -> dict:
    return {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "test.local"},
        "requestContext": {
            "http": {"method": method, "path": path, "sourceIp": "127.0.0.1"},
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }


def test_handler_serves_health():
    from cidy_api.lambda_handler import handler

    resp = handler(_http_event("GET", "/health"), None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_lambda_handler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy_api.lambda_handler'` (or `No module named 'mangum'`).

- [ ] **Step 3: Add dependency and implement the handler**

In `backend/pyproject.toml`, add `"mangum>=0.17,<1"` to the `dependencies` list (alongside fastapi etc.).

`backend/cidy_api/lambda_handler.py`:
```python
from __future__ import annotations

from mangum import Mangum

from cidy_api.app import create_app

app = create_app()
handler = Mangum(app, lifespan="off")
```

- [ ] **Step 4: Install and run the test**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/api/test_lambda_handler.py -v`
Expected: PASS (the synthetic HTTP API event is routed through Mangum to the `/health` endpoint; no AWS or DB needed).

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/cidy_api/lambda_handler.py backend/tests/api/test_lambda_handler.py
git commit -m "feat: add Mangum Lambda handler for the API"
```

---

### Task 2: SAM template and Lambda packaging

**Files:**
- Create: `template.yaml` (repo root)
- Create: `backend/requirements.txt`
- Create: `backend/tests/api/test_sam_template.py`

**Interfaces:**
- Consumes: `cidy_api.lambda_handler.handler` (Task 1) as the Lambda `Handler`.
- Produces: a SAM template declaring `CidyFunction` (Serverless::Function, runtime python3.12), `CidyHttpApi` (Serverless::HttpApi), `CidyDatabase` (RDS::DBInstance, postgres, publicly accessible), and `CidyDbSecurityGroup`; with `CIDY_DEV_MODE="false"` and a `CIDY_DATABASE_URL` built from the RDS endpoint. `backend/requirements.txt` lists the Lambda's runtime deps.

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_sam_template.py`:
```python
from pathlib import Path

import yaml

TEMPLATE = Path(__file__).resolve().parents[2] / "template.yaml"


class _CfnLoader(yaml.SafeLoader):
    pass


def _ignore_cfn_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


_CfnLoader.add_multi_constructor("!", _ignore_cfn_tag)


def _load() -> dict:
    return yaml.load(TEMPLATE.read_text(encoding="utf-8"), Loader=_CfnLoader)


def test_is_sam_template():
    assert _load()["Transform"] == "AWS::Serverless-2016-10-31"


def test_function_runtime_handler_and_prod_env():
    fn = _load()["Resources"]["CidyFunction"]
    assert fn["Type"] == "AWS::Serverless::Function"
    assert fn["Properties"]["Runtime"] == "python3.12"
    assert fn["Properties"]["Handler"] == "cidy_api.lambda_handler.handler"
    env = fn["Properties"]["Environment"]["Variables"]
    assert env["CIDY_DEV_MODE"] == "false"
    assert "CIDY_DATABASE_URL" in env and "CIDY_JWT_SECRET" in env


def test_database_is_postgres():
    db = _load()["Resources"]["CidyDatabase"]
    assert db["Type"] == "AWS::RDS::DBInstance"
    assert db["Properties"]["Engine"] == "postgres"


def test_jwt_secret_param_is_noecho_min32():
    p = _load()["Parameters"]["JwtSecret"]
    assert p["NoEcho"] is True
    assert p["MinLength"] == 32


def test_requirements_lists_runtime_deps():
    reqs = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text(encoding="utf-8")
    for pkg in ("fastapi", "mangum", "sqlalchemy", "psycopg", "pydantic", "pyjwt"):
        assert pkg in reqs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_sam_template.py -v`
Expected: FAIL — `FileNotFoundError` for `template.yaml`.

- [ ] **Step 3: Author the template and requirements**

`template.yaml` (repo root):
```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: >
  CIdy Drafting Companion backend (DEV deployment). NOTE: this posture is dev-only —
  the database is publicly reachable and the Lambda runs outside a VPC. Do not use as-is
  for production; harden with a VPC, private RDS, and RDS Proxy first.

Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC for the database security group (e.g. your account's default VPC).
  JwtSecret:
    Type: String
    NoEcho: true
    MinLength: 32
    Description: Strong JWT signing secret (>= 32 characters).
  AppBaseUrl:
    Type: String
    Default: https://placeholder.execute-api.amazonaws.com
    Description: Public base URL of the deployed API (re-deploy with the real ApiUrl after first deploy).
  DbName:
    Type: String
    Default: cidy
  DbMasterUsername:
    Type: String
    Default: cidy
  DbMasterPassword:
    Type: String
    NoEcho: true
    MinLength: 8
    Description: Master password for the RDS PostgreSQL instance.
  DbInstanceClass:
    Type: String
    Default: db.t3.micro
  DbAllocatedStorage:
    Type: Number
    Default: 20

Resources:
  CidyDbSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: CIdy RDS access (DEV - open to the internet on 5432)
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          CidrIp: 0.0.0.0/0
          Description: DEV ONLY - publicly reachable Postgres

  CidyDatabase:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Delete
    Properties:
      Engine: postgres
      DBName: !Ref DbName
      MasterUsername: !Ref DbMasterUsername
      MasterUserPassword: !Ref DbMasterPassword
      DBInstanceClass: !Ref DbInstanceClass
      AllocatedStorage: !Ref DbAllocatedStorage
      PubliclyAccessible: true
      VPCSecurityGroups:
        - !Ref CidyDbSecurityGroup

  CidyHttpApi:
    Type: AWS::Serverless::HttpApi

  CidyFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: backend/
      Handler: cidy_api.lambda_handler.handler
      Runtime: python3.12
      Architectures:
        - x86_64
      Timeout: 30
      MemorySize: 512
      Environment:
        Variables:
          CIDY_DATABASE_URL: !Sub "postgresql+psycopg://${DbMasterUsername}:${DbMasterPassword}@${CidyDatabase.Endpoint.Address}:${CidyDatabase.Endpoint.Port}/${DbName}"
          CIDY_JWT_SECRET: !Ref JwtSecret
          CIDY_DEV_MODE: "false"
          CIDY_APP_BASE_URL: !Ref AppBaseUrl
      Events:
        Proxy:
          Type: HttpApi
          Properties:
            ApiId: !Ref CidyHttpApi
            Path: /{proxy+}
            Method: ANY
        Root:
          Type: HttpApi
          Properties:
            ApiId: !Ref CidyHttpApi
            Path: /
            Method: ANY

Outputs:
  ApiUrl:
    Description: Base URL of the deployed HTTP API
    Value: !Sub "https://${CidyHttpApi}.execute-api.${AWS::Region}.amazonaws.com"
  DbEndpoint:
    Description: RDS endpoint address
    Value: !GetAtt CidyDatabase.Endpoint.Address
```

`backend/requirements.txt` (runtime deps for the Lambda; `alembic` is excluded — migrations run from a workstation, not in the function):
```text
fastapi>=0.110,<1
mangum>=0.17,<1
pydantic>=2.6,<3
pydantic-settings>=2.2,<3
sqlalchemy>=2.0,<3
psycopg[binary]>=3.1,<4
pyjwt>=2.8,<3
email-validator>=2.1
```

- [ ] **Step 4: Run the structure test, then validate the template with SAM**

Run (Git Bash): `cd backend && python -m pytest tests/api/test_sam_template.py -v`
Expected: PASS (6 tests).

Then validate the template with the SAM CLI **via the PowerShell tool** (sam is not on the Git Bash PATH), from the repo root:
```
sam validate --region us-east-1 --template template.yaml
sam validate --region us-east-1 --lint --template template.yaml
```
Expected: `sam validate` prints that `template.yaml` is a valid SAM Template. `--lint` (cfn-lint) is EXPECTED to emit security warnings about the publicly-open security group ingress (`0.0.0.0/0` on 5432) — that is the deliberate dev posture, not a defect. The verification passes as long as there are **no validation errors** (warnings are acceptable). Record the full output in the task report. If `--lint` reports actual ERRORS (not warnings), fix the template.

- [ ] **Step 5: Commit**

```bash
git add template.yaml backend/requirements.txt backend/tests/api/test_sam_template.py
git commit -m "feat: add SAM template and Lambda runtime requirements"
```

---

### Task 3: Deploy config and runbook

**Files:**
- Create: `samconfig.toml` (repo root)
- Create: `DEPLOY.md` (repo root)
- Create: `backend/tests/api/test_deploy_docs.py`

**Interfaces:**
- Consumes: `template.yaml` (Task 2).
- Produces: `samconfig.toml` (default deploy parameters) and `DEPLOY.md` (a complete runbook: build, deploy, post-deploy DB migration, re-deploy with the real API URL, SES-later note, Aurora alternative, teardown, and the dev-security caveat).

- [ ] **Step 1: Write the failing test**

`backend/tests/api/test_deploy_docs.py`:
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_samconfig_exists():
    assert (ROOT / "samconfig.toml").exists()


def test_deploy_md_covers_key_steps():
    text = (ROOT / "DEPLOY.md").read_text(encoding="utf-8").lower()
    for needle in [
        "sam build",
        "sam deploy",
        "alembic upgrade head",
        "cidy_jwt_secret",
        "cidy_dev_mode",
        "sam delete",
        "ses",
        "aurora",
    ]:
        assert needle in text, f"DEPLOY.md is missing: {needle}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_deploy_docs.py -v`
Expected: FAIL — `FileNotFoundError` for `samconfig.toml` / `DEPLOY.md`.

- [ ] **Step 3: Author the config and runbook**

`samconfig.toml` (repo root):
```toml
version = 0.1

[default.deploy.parameters]
stack_name = "cidy-backend-dev"
resolve_s3 = true
capabilities = "CAPABILITY_IAM"
region = "us-east-1"
confirm_changeset = true
```

`DEPLOY.md` (repo root):
```markdown
# Deploying the CIdy Backend (dev)

> **Security note:** this template is a **dev** posture — the PostgreSQL database is
> publicly reachable and the Lambda runs outside a VPC. Do not use it as-is for
> production. Harden first with a VPC, a private RDS subnet, and RDS Proxy.

## Prerequisites
- AWS credentials configured (`aws sts get-caller-identity` works).
- AWS SAM CLI installed (`sam --version`). On Windows, run `sam` from PowerShell.
- The VPC id to host the DB security group (your default VPC is fine):
  `aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text`

## 1. Build
```
sam build
```
(`sam build` packages `backend/` and installs `backend/requirements.txt`. Native build uses
local Python; if the Lambda runtime differs, use `sam build --use-container` with Docker.)

## 2. Deploy
```
sam deploy --guided
```
Supply parameters when prompted (or set them in `samconfig.toml`):
- `VpcId` — your default VPC id
- `JwtSecret` — a strong secret, **>= 32 characters**, wired into the function as
  `CIDY_JWT_SECRET` (the app refuses to boot in non-dev mode with a weak/default secret)
- `DbMasterPassword` — a strong DB password (>= 8 chars)
- `AppBaseUrl` — leave the placeholder for the first deploy; update it in step 4

The function runs with `CIDY_DEV_MODE=false`, so `dev_link` is NOT returned by
`/auth/magic-link` (email is still mocked — see SES note below).

After deploy, note the stack outputs `ApiUrl` and `DbEndpoint`.

## 3. Run database migrations
The function does NOT create tables (no `create_all` in production). From a workstation
that can reach the public RDS endpoint, run the Alembic migrations once:
```
cd backend
CIDY_DATABASE_URL="postgresql+psycopg://<user>:<password>@<DbEndpoint>:5432/cidy" \
  python -m alembic upgrade head
```
This applies `0001_initial` and `0002_artifacts`.

## 4. Re-point the app at its real URL
Re-deploy with `AppBaseUrl` set to the `ApiUrl` output so magic links use the real host:
```
sam deploy --parameter-overrides AppBaseUrl=<ApiUrl>
```

## 5. Smoke test
```
curl <ApiUrl>/health        # {"status":"ok"}
curl <ApiUrl>/schemas       # list of template schemas
```

## Email (SES) — deferred
SES is not wired in this phase. With `CIDY_DEV_MODE=false`, `email_sink.send_magic_link`
raises `NotImplementedError`, so a future change must implement SES delivery (verify a
sender identity, add `ses:SendEmail` to the function role, request sandbox exit) before
magic-link login works end-to-end in a deployed environment.

## Database alternative — Aurora Serverless v2
This template uses a single RDS PostgreSQL instance for simplicity. To use Aurora
Serverless v2 instead, replace `CidyDatabase` with an `AWS::RDS::DBCluster`
(`EngineMode: provisioned`, `ServerlessV2ScalingConfiguration`) plus an
`AWS::RDS::DBInstance` of class `db.serverless`, and update the `CIDY_DATABASE_URL`
to point at the cluster endpoint.

## Teardown
```
sam delete
```
Removes the stack, including the database (the template sets `DeletionPolicy: Delete`
on the DB — take a snapshot first if you need the data).
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_deploy_docs.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full suite and commit**

Run: `cd backend && python -m pytest -q`
Expected: all tests (Phases 1/2A/2B + the three Phase 2C tests) PASS.

```bash
git add samconfig.toml DEPLOY.md backend/tests/api/test_deploy_docs.py
git commit -m "feat: add SAM deploy config and deployment runbook"
```

---

## Phase 2C completion

At the end of this plan the repository contains everything needed to deploy the CIdy
backend to AWS — a Mangum Lambda adapter (unit-tested against a synthetic API Gateway
event), a `sam validate`-clean SAM template provisioning Lambda + HTTP API + PostgreSQL
RDS, runtime requirements, deploy config, and a step-by-step runbook including the
post-deploy Alembic migration — all validated locally with no live AWS resources created.

## Notes carried forward

- **Production hardening:** VPC + private RDS subnets + RDS Proxy (connection pooling for
  Lambda + Postgres), tighter security-group ingress, secrets via AWS Secrets Manager
  rather than CloudFormation `NoEcho` parameters.
- **SES email delivery:** implement `email_sink.send_magic_link` for the non-dev path,
  add `ses:SendEmail` to the function role, verify a sender identity, request sandbox exit.
- **`UNIQUE(artifact_id, version_no)` backstop** on `artifact_versions` (carried from Phase 2B).
- **CI:** run `alembic upgrade head` against a pristine database and `sam validate --lint`
  in CI; build/deploy on merge to `master`.
- An actual `sam deploy` to a live stack remains a deliberate, user-initiated step.
