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
