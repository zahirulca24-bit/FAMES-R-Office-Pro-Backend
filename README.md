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

# Controlled Backend Delivery Roadmap — 18 PRs

## Execution rule

Work is delivered **head by head**. A head is complete only when every PR under it is merged and the head-level completion gate passes.

The next head must not start until the current head has passed:

- implementation review
- migration upgrade test
- migration downgrade/re-upgrade test where applicable
- automated test suite
- role and permission tests
- data-integrity tests
- API contract tests
- deployment readiness check
- relevant frontend integration verification

Checklist convention:

- `[ ]` Not started or not verified
- `[x]` Implemented, tested, reviewed, and merged

A PR must not be ticked merely because code was written. It is ticked only after CI and the defined acceptance tests pass.

---

## Head 1 — Platform Foundation & Security

**Head status:** [ ] Not complete

- [ ] **PR-BE-01 — Backend Standards, Permission Catalogue & Audit Event Foundation**
  - Standard API success/error envelope
  - Error-code catalogue
  - Correlation/request ID
  - Permission catalogue
  - Role-permission mapping foundation
  - Portfolio/engagement access evaluator skeleton
  - Audit-event and activity-event foundations
  - Naming, soft-delete, archive and versioning conventions
  - Migration, tests and architecture documentation

- [ ] **PR-BE-02 — Effective Access Control & Record-Level Authorization**
  - Role + firm membership + portfolio + engagement + confidentiality evaluation
  - Deny-by-default access policy
  - Sensitive-field masking foundation
  - Delegation and temporary access model
  - Authorization decision tests

- [ ] **PR-BE-03 — Workflow, Policy, Approval & Locking Foundation**
  - Workflow definitions, states and transitions
  - Policy gate evaluation
  - Approval actions and immutable approval history
  - Rejection/reassignment/delegation controls
  - Generic lock, reopen and revision governance

### Head 1 completion gate

- [ ] All three PRs merged
- [ ] Permission-denial tests pass
- [ ] Audit events are append-only
- [ ] Workflow transitions reject unauthorized actions
- [ ] Lock/reopen controls pass
- [ ] Full CI green

---

## Head 2 — Client Master & Relationship Management

**Head status:** [ ] Not complete

- [ ] **PR-BE-04 — Client Master Schema & Linked Records**
  - Client identity and immutable client code
  - Contacts and addresses
  - TIN, BIN, RJSC and other identifiers
  - Directors and shareholders
  - Client groups and relationships
  - Status history and audit events

- [ ] **PR-BE-05 — Client Lifecycle, Duplicate Detection & Risk Profile**
  - Prospect-to-archive lifecycle
  - Conflict-check state
  - Duplicate blocking and similarity warning
  - Client risk profile
  - Service activation and partner ownership
  - Archive/restore controls

- [ ] **PR-BE-06 — Client API, Search, Export & Frontend Integration Contract**
  - Create, read, update and archive APIs
  - Search, filters, sorting and pagination
  - Permission-controlled export
  - Activity timeline
  - Frontend API contract and persistence tests

### Head 2 completion gate

- [ ] All three PRs merged
- [ ] Real client survives refresh and re-login
- [ ] Duplicate identifiers are blocked
- [ ] Unauthorized portfolio access is denied
- [ ] Client lifecycle and archive/restore tests pass
- [ ] Full CI green

---

## Head 3 — Staff, Capacity & Worklogs

**Head status:** [ ] Not complete

- [ ] **PR-BE-07 — Staff Master, Department, Designation & Reporting Line**
  - Staff profile
  - Department and designation
  - Supervisor/reporting hierarchy
  - Skills and employment status
  - Staff confidentiality controls

- [ ] **PR-BE-08 — Attendance, Leave, Capacity, Assignment & Worklogs**
  - Attendance and leave foundation
  - Available and assigned capacity
  - Task and engagement worklogs
  - Billable/non-billable classification
  - Timesheet review and locking

### Head 3 completion gate

- [ ] Both PRs merged
- [ ] Staff permissions protect salary/cost fields
- [ ] Capacity calculations reconcile
- [ ] Worklog totals and locks pass
- [ ] Attendance and leave integrity tests pass
- [ ] Full CI green

---

## Head 4 — Engagement, Tasks & Operational Workflow

**Head status:** [ ] Not complete

- [ ] **PR-BE-09 — Engagement Core, Naming Series & Team Assignment**
  - Engagement identity and code
  - Client and service linkage
  - Partner, manager, reviewer and team assignments
  - Fee, period, priority, deadline and status
  - Engagement access boundary

- [ ] **PR-BE-10 — Engagement Templates & Automatic Task Generation**
  - Service-specific templates
  - Standard stages and tasks
  - Required documents
  - Default approval chain
  - Deadline and milestone generation

- [ ] **PR-BE-11 — Task, Dependency, Deadline & Weighted Progress Engine**
  - Parent/child tasks
  - Task dependencies
  - Assignment and reviewer control
  - Deadline and escalation state
  - Weighted engagement progress

- [ ] **PR-BE-12 — Engagement Workflow, Review Queue & Final Closure Controls**
  - Planning-to-finalization lifecycle
  - Review and partner approval queues
  - Completion blockers
  - Closure checklist
  - Lock, reopen and revised-lock process

### Head 4 completion gate

- [ ] All four PRs merged
- [ ] One real engagement can be created and assigned
- [ ] Template tasks generate correctly
- [ ] Dependency and deadline rules pass
- [ ] Weighted progress reconciles
- [ ] Unauthorized closure/reopen attempts fail
- [ ] Full CI green

---

## Head 5 — Documents, Evidence & Working Papers

**Head status:** [ ] Not complete

- [ ] **PR-BE-13 — Private Document Storage, Metadata, Versioning & Access Logs**
  - Private object storage integration
  - Document metadata and classification
  - Version history and checksum
  - Upload/download authorization
  - Duplicate detection foundation
  - Retention, archive and access logs

- [ ] **PR-BE-14 — Working Paper, Evidence Linkage, Review Notes & Sign-Off**
  - Working-paper lifecycle
  - Preparer, reviewer and partner sign-off
  - Supporting evidence linkage
  - Review notes and response trail
  - Cross-reference and revision history
  - Final lock and controlled reopen

### Head 5 completion gate

- [ ] Both PRs merged
- [ ] Unauthorized document download is blocked
- [ ] Document version history is retained
- [ ] Working-paper sign-off sequence passes
- [ ] Review-note resolution is traceable
- [ ] Locked working papers cannot be silently edited
- [ ] Full CI green

---

## Head 6 — Audit Practice Engine

**Head status:** [ ] Not complete

- [ ] **PR-BE-15 — Audit Planning, Acceptance, Independence, Materiality & Risk**
  - Engagement acceptance/continuance
  - Conflict and independence declarations
  - Audit planning
  - Materiality
  - Risk, assertion and response mapping
  - Audit programme foundation

- [ ] **PR-BE-16 — Requisition, Testing, Issues, Completion & Finalization**
  - Document requisitions and follow-up
  - Procedure assignment and execution
  - Sampling/testing result records
  - Audit issues and exception register
  - Completion checklist
  - Partner finalization and locked archive

### Head 6 completion gate

- [ ] Both PRs merged
- [ ] Acceptance and independence gates pass
- [ ] Risk-to-procedure linkage is complete
- [ ] Requisition trail is traceable
- [ ] Open high-risk issues block finalization
- [ ] Complete audit file can be locked
- [ ] Full CI green

---

## Head 7 — Finance, Reporting & Production Hardening

**Head status:** [ ] Not complete

- [ ] **PR-BE-17 — Fees, Invoices, Receipts, Expenses & Engagement Economics**
  - Fee schedule
  - Fixed, milestone, hourly and retainer billing modes
  - Invoice and receipt allocation
  - Advance and outstanding tracking
  - Engagement expenses and staff-cost linkage
  - Profitability, realization and aging metrics
  - Finance period and engagement-finance locks

- [ ] **PR-BE-18 — Dashboards, Reports, Notifications, Backup & Production Hardening**
  - Partner, manager and staff dashboards
  - Operational and management reports
  - Deadline and approval notifications
  - Export controls
  - Performance and security tests
  - Backup/restore verification
  - Production migration rehearsal
  - Final live-use readiness audit

### Head 7 completion gate

- [ ] Both PRs merged
- [ ] Invoice, receipt and outstanding balances reconcile
- [ ] Engagement profitability reconciles
- [ ] Dashboard data matches source records
- [ ] Notification triggers pass
- [ ] Backup and restore test succeeds
- [ ] Production readiness audit passes
- [ ] Full CI green

---

# Overall Backend Completion Checklist

- [ ] Head 1 — Platform Foundation & Security
- [ ] Head 2 — Client Master & Relationship Management
- [ ] Head 3 — Staff, Capacity & Worklogs
- [ ] Head 4 — Engagement, Tasks & Operational Workflow
- [ ] Head 5 — Documents, Evidence & Working Papers
- [ ] Head 6 — Audit Practice Engine
- [ ] Head 7 — Finance, Reporting & Production Hardening

## Final backend completion gate

The backend may be marked complete only when:

- [ ] All 18 PRs are merged and individually checked
- [ ] All seven head completion gates pass
- [ ] No active business module uses mock or in-memory persistence
- [ ] Role, portfolio, engagement and confidentiality access tests pass
- [ ] One real client and one full engagement complete the end-to-end flow
- [ ] One audit file reaches finalization and lock
- [ ] Documents, finance and dashboards reconcile from the same source data
- [ ] Critical actions are traceable in immutable audit history
- [ ] Backup and restore testing succeeds
- [ ] Production deployment and `/health/ready` return HTTP 200

## Current phase

**Head 1 — Platform Foundation & Security: NOT STARTED**

The first implementation target is **PR-BE-01 — Backend Standards, Permission Catalogue & Audit Event Foundation**.
