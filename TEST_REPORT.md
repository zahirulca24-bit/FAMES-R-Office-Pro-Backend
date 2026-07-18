# Batch 1 Test Report

## Verdict

**Automated local verification: PASS with one non-failing upstream deprecation warning.**

- Automated tests: 20 passed
- Failed tests: 0
- Deployment tests: not run
- Live PostgreSQL tests: not run because no live database credentials or instance were available
- Independent audit: pending

## Execution Environment

- Execution date: July 19, 2026
- Local Python: 3.13.5
- Isolated virtual environment: `/tmp/fames_batch1_final_venv`
- Target deployment Python declared in `render.yaml`: 3.12.8

## Coverage Executed

### Authentication

- Exact frontend login request/response contract
- Bearer-token `/auth/me`
- Invalid and unknown credentials
- Failed-login lockout
- Password change
- Old-password rejection after change
- Existing-token revocation after password change

### Foundational RBAC

- Non-Super-Admin denied from Admin API
- Forced-password-change user denied from privileged operation
- Super Admin create-user baseline
- Duplicate login/email rejection
- Self-disable protection
- Session revocation after account status change implementation path

### Bootstrap and Recovery

- Normal bootstrap preserves an existing suspended account and password
- Emergency recovery is explicit and Super-Admin-only
- Emergency recovery resets only the named account
- Existing sessions are revoked after recovery

### Configuration and CORS

- Production SQLite rejection
- Placeholder JWT-secret rejection
- Wildcard CORS rejection
- Configured origin allowed
- Unconfigured origin denied
- PostgreSQL driver import and URL normalization

### Database and Migration

- Fresh SQLite migration
- Current Alembic head
- Legacy pre-Alembic database adoption
- `token_version` addition
- Readiness database/schema/revision checks
- PostgreSQL-dialect offline SQL compilation
- Destructive baseline downgrade blocked by implementation policy

### Batch Boundary

- OpenAPI confirms no Client or Job routes were added
- Client/Job functional regression was not possible because those modules do not exist in the current backend and remain locked to Batches 2 and 3

## Initial Packaging Defect Found and Corrected

Before final verification, `pip install -e .[dev]` failed with:

```text
error: Multiple top-level packages discovered in a flat-layout: ['app', 'migrations'].
```

Explicit setuptools package discovery was added. The final clean-environment install output below proves the corrected package builds successfully.

## Actual Command Output

```text
$ python --version
Python 3.13.5

$ /tmp/fames_batch1_final_venv/bin/python -m pip install -e '.[dev]'
Successfully built fames-r-office-pro-backend
Successfully installed Mako-1.3.12 MarkupSafe-3.0.3 PyJWT-2.13.0 alembic-1.18.5 annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.14.2 argon2-cffi-25.1.0 argon2-cffi-bindings-25.1.0 certifi-2026.6.17 cffi-2.1.0 click-8.4.2 dnspython-2.8.0 email-validator-2.3.0 fames-r-office-pro-backend-0.1.1 fastapi-0.139.2 greenlet-3.5.3 h11-0.16.0 httpcore-1.0.9 httptools-0.8.0 httpx-0.28.1 idna-3.18 iniconfig-2.3.0 packaging-26.2 pluggy-1.6.0 psycopg-3.3.4 psycopg-binary-3.3.4 pycparser-3.0 pydantic-2.13.4 pydantic-core-2.46.4 pydantic-settings-2.14.2 pygments-2.20.0 pytest-9.1.1 python-dotenv-1.2.2 pyyaml-6.0.3 sqlalchemy-2.0.51 starlette-1.3.1 typing-extensions-4.16.0 typing-inspection-0.4.2 uvicorn-0.51.0 uvloop-0.22.1 watchfiles-1.2.0 websockets-16.1.1

$ /tmp/fames_batch1_final_venv/bin/python -m pip check
WARNING: The directory '/home/oai/.cache/pip' or its parent directory is not owned or is not writable by the current user. The cache has been disabled. Check the permissions and owner of that directory. If executing pip with sudo, you should use sudo's -H flag.
No broken requirements found.

$ /tmp/fames_batch1_final_venv/bin/pytest -q
....................                                                     [100%]
=============================== warnings summary ===============================
../../../tmp/fames_batch1_final_venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  /tmp/fames_batch1_final_venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
20 passed, 1 warning in 5.81s

$ /tmp/fames_batch1_final_venv/bin/python -m compileall -q app scripts migrations
compileall: PASS

$ /tmp/fames_batch1_final_venv/bin/alembic heads
20260719_01 (head)

$ DATABASE_URL=sqlite:///./final_verify.db alembic upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 20260719_01, Batch 1 auth baseline and token revocation support.

$ DATABASE_URL=sqlite:///./final_verify.db alembic current
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
20260719_01 (head)

$ SQLite schema inspection
revision: 20260719_01
tables: alembic_version, auth_audit_logs, auth_users
auth_users.token_version: present

$ PostgreSQL offline migration compilation
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 20260719_01, Batch 1 auth baseline and token revocation support.
CREATE TABLE auth_users (
CREATE TABLE auth_audit_logs (
INSERT INTO alembic_version (version_num) VALUES ('20260719_01') RETURNING alembic_version.version_num;
COMMIT;

$ API route inventory
POST         /api/v1/admin/users
PATCH        /api/v1/admin/users/{login_id}/status
POST         /api/v1/auth/change-password
POST         /api/v1/auth/login
GET          /api/v1/auth/me
GET          /api/v1/health
GET          /api/v1/health/live
GET          /api/v1/health/ready
GET          /health
```

## Warning Disclosure

The test suite emitted one `StarletteDeprecationWarning` from the installed FastAPI/Starlette TestClient stack. It did not fail tests. This report does not claim the warning is resolved.

## Unverified Items

1. Live PostgreSQL connection, migration, persistence, restart persistence, and rollback/backup behavior.
2. Python 3.12.8 runtime execution.
3. Render build/runtime/deployment.
4. Frontend browser end-to-end login against a deployed backend.
5. Client and Job behavior, because those modules are not present in the current backend and are reserved for later batches.

## Clean Package Scan Output

```text
$ clean backend package scan
files: 30
forbidden_artifacts: none
high_risk_secret_patterns: none
frontend_source_files: 0
nested_archives: 0
```
