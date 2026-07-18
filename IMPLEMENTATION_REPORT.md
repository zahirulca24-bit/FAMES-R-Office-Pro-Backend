# Batch 1 Implementation Report

## Status

**READY FOR AUDIT — NOT APPROVED**

Branch: `batch-1-recovery-stabilization`

No deployment was performed. No Batch 2–8 feature was implemented.

## Implemented Scope

### Clean backend package

- Reconstructed a backend-only package containing Python application code, Alembic migrations, tests, configuration templates, and required reports.
- Expanded `.gitignore` to exclude environments, secrets, caches, local databases, logs, frontend folders, `node_modules`, archives, and build output.
- Corrected setuptools package discovery so `pip install -e .[dev]` succeeds after adding Alembic.

### Frontend authentication contract preservation

The current frontend contract was inspected before backend changes. The following contract remains unchanged:

- `POST /api/v1/auth/login` body: `login_id`, `password`, `remember_me`
- Login response: `access_token`, `token_type`, `expires_in`, `user`
- `GET /api/v1/auth/me` with bearer token
- `POST /api/v1/auth/change-password` body: `current_password`, `new_password`

Automated tests assert the exact login response top-level fields expected by the frontend.

### Password and session security

- Retained Argon2 password hashing.
- Added a dummy Argon2 verification path for unknown login IDs to reduce username-enumeration timing differences.
- Added JWT issuer, audience, token ID, not-before, and required-claim validation.
- Added per-user `token_version`; password changes and status changes revoke existing sessions.
- Users forced to change a temporary/recovered password cannot perform privileged Admin operations before changing it.
- No unauthenticated password-reset endpoint was introduced. Recovery remains server-side and environment-controlled.

### Admin bootstrap and recovery

- Normal bootstrap creates missing configured users only.
- Existing accounts are not reactivated, reassigned, or password-reset during restart.
- Emergency recovery requires both `BOOTSTRAP_FORCE_RESET=true` and an explicit `BOOTSTRAP_RECOVERY_LOGIN_ID`.
- Emergency recovery is restricted to a configured `SUPER_ADMIN`.
- Recovery processes only the named target, clears lock state, activates the target, forces a password change, and revokes existing sessions.
- Runtime passwords remain environment variables; no production password is stored in source.

### PostgreSQL, SQLAlchemy, and Alembic

- Added Alembic dependency and configuration.
- Added revision `20260719_01` as an adoption baseline for databases previously created through SQLAlchemy `create_all()`.
- The migration creates fresh auth tables or adds `token_version` to an existing auth table.
- Fresh PostgreSQL SQL generation is supported with `alembic upgrade head --sql`.
- Unsafe automatic `Base.metadata.create_all()` was removed from application startup.
- The adoption baseline has a deliberately blocked destructive downgrade because the tables may predate Alembic.
- PostgreSQL driver installation and URL normalization were tested without a live database connection.

### Production configuration and CORS

Production startup rejects:

- SQLite database URLs
- Known placeholder JWT secrets
- Unsupported JWT algorithms
- Wildcard CORS origins
- Empty or malformed CORS origins
- Localhost origins in production

CORS methods and headers are explicit rather than wildcarded.

### Health and readiness

Added:

- `GET /api/v1/health/live` — process liveness only
- `GET /api/v1/health/ready` — verifies startup bootstrap state, database connectivity, required tables, required auth columns, and Alembic revision

Legacy health endpoints remain available to avoid breaking existing integrations.

### Foundational RBAC

- The current user is loaded from the database for every protected operation.
- Inactive users and revoked token versions are rejected.
- Admin endpoints require an active `SUPER_ADMIN` whose forced password change is complete.
- User status changes revoke existing sessions.
- Full role-permission mapping, overrides, last-active-Super-Admin policy, and complete user lifecycle remain locked to Batch 2.

## Scope Boundary Confirmation

No Client, Job, Work Station, Audit Engine, Drive, Communication, Staff, Notification, or AI feature was added. OpenAPI regression tests confirm that `/api/v1/clients` and `/api/v1/jobs` routes were not introduced.

## Exact Remaining Gaps

1. Independent audit has not yet approved Batch 1.
2. No Render deployment was performed, as instructed.
3. No live PostgreSQL credentials or instance were available; live PostgreSQL persistence was therefore not proven. PostgreSQL driver loading, production URL validation, and PostgreSQL-dialect Alembic SQL compilation were verified.
4. The available execution environment used Python 3.13.5, while `render.yaml` declares Python 3.12.8; Python 3.12 runtime execution was not available locally.
5. Client and Job APIs do not exist in the current backend. Functional Client/Job regression tests cannot exist until their locked implementation batches; Batch 1 tests instead verify that later-batch routes were not mixed in.
6. A TestClient deprecation warning from the installed FastAPI/Starlette stack remains non-failing and is recorded in `TEST_REPORT.md`. Dependency modernization is not claimed as complete.

## Audit Decision

The project owner or independent auditor must decide whether to mark Batch 1 `APPROVED` or `CORRECTION REQUIRED`.
