# FAMES & R Office PRO — Backend

FastAPI backend for **FAMES & R Office PRO**.

## Current implemented scope

- Custom JWT authentication
- Argon2 password hashing
- Login failure lockout and authentication audit logs
- Current-user and password-change endpoints
- Super Admin user creation and account-status controls
- SQLAlchemy models and Alembic migration foundation
- Liveness and database-backed readiness endpoints

Client management, staff operations, jobs, audit workflow, Google Drive integration, notifications, AI assistance, dashboards, and reporting are not yet implemented.

## Technology

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL in production
- SQLite for local development and tests

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -q
```

The GitHub Actions workflow also verifies Python compilation, PostgreSQL migration upgrade, downgrade/re-upgrade, and the test suite.

## Railway deployment

`railway.toml` is the source-controlled deployment configuration. Railway will:

1. Build the Python project with Railpack.
2. Run `alembic upgrade head` as the pre-deploy migration.
3. Start Uvicorn on Railway's injected `$PORT`.
4. Require `/health/ready` to return HTTP 200 before activating the deployment.

Required production variables:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=<unique random value, at least 32 characters>
CORS_ORIGINS=https://<approved-frontend-domain>
```

Optional one-time bootstrap variables are documented in `.env.example`. Remove bootstrap passwords immediately after the intended accounts are created. Use `BOOTSTRAP_FORCE_RESET=true` only for a controlled emergency recovery and remove it immediately afterward.

## API endpoints currently available

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/change-password
POST /api/v1/admin/users
PATCH /api/v1/admin/users/{login_id}/status
GET  /health
GET  /health/live
GET  /health/ready
GET  /api/v1/health
```

## Production schema policy

Alembic is the only production schema-change mechanism. Automatic SQLAlchemy `create_all()` is limited to non-production development/test execution.

## Current phase

**Phase 1 — Backend stabilization: IN PROGRESS**

Deployment or migration success must not be claimed until GitHub CI passes and the live Railway deployment returns HTTP 200 from `/health/ready`.
