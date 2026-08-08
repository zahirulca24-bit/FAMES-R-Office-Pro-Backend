# FAMES & R Office PRO — Backend

FastAPI backend for **FAMES & R Office PRO**, a firm-only CA practice management, audit, compliance and operations platform.

## Technology

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL in production
- SQLite for local development/tests
- JWT + Argon2 authentication

## Current implemented scope

- Authentication, password-change and login protection
- Super Admin user administration
- Permission catalogue and deny-by-default authorization foundation
- Record-level access, delegation and confidentiality controls
- Audit events, activity events and correlation IDs
- Workflow/policy/approval/locking foundation
- Client Master schema and linked records
- Client lifecycle, conflict-check, risk, services and portfolio ownership
- Real database-backed Client CRUD/search/export/activity APIs
- Staff Master, departments, designations, reporting hierarchy and skills
- Attendance, leave, capacity assignments and controlled worklogs
- Engagement Master, naming series, team assignment and engagement-level access boundary
- Engagement templates with automatic task and required-document generation
- Task dependency, lifecycle, deadline escalation and weighted engagement progress engine
- Engagement review queue, completion blockers, final closure, lock and controlled reopen
- Private document storage, version history, integrity hashes and access logs
- Working papers with evidence linkage, review notes, sign-off history and locked-file immutability
- Audit acceptance, independence, materiality, risk register and risk-to-procedure planning controls
- Audit requisitions, testing, issues, completion readiness and final audit-file locking
- Fees, invoices, receipts, engagement expenses and engagement economics reconciliation
- Optimistic version conflict protection and archive controls
- Liveness and database-backed readiness endpoints

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

GitHub Actions verifies Python compilation, Alembic history, clean PostgreSQL upgrade, downgrade/re-upgrade, and the automated test suite.

## Production schema policy

Alembic is the only production schema-change mechanism. Automatic SQLAlchemy `create_all()` is restricted to development/test execution.

# Controlled Backend Delivery Roadmap — 18 PRs

## Execution rule

Work is delivered **head by head**. A PR is checked only after implementation, CI, tests, review and merge. A head must pass its completion gate before the next head starts.

---

## Head 1 — Platform Foundation & Security

**Head status: [x] COMPLETE**

- [x] **PR-BE-01 — Backend Standards, Permission Catalogue & Audit Event Foundation**
- [x] **PR-BE-02 — Effective Access Control & Record-Level Authorization**
- [x] **PR-BE-03 — Workflow, Policy, Approval & Locking Foundation**

### Head 1 completion gate

- [x] All three PRs merged
- [x] Permission-denial tests pass
- [x] Audit-event foundation verified
- [x] Workflow transition controls verified
- [x] Lock/reopen controls verified
- [x] Full CI green

---

## Head 2 — Client Master & Relationship Management

**Head status: [x] COMPLETE**

- [x] **PR-BE-04 — Client Master Schema & Linked Records**
- [x] **PR-BE-05 — Client Lifecycle, Duplicate Detection & Risk Profile**
- [x] **PR-BE-06 — Client API, Search, Export & Frontend Integration Contract**

### Head 2 completion gate

- [x] All three PRs merged
- [x] Database-backed client persistence verified
- [x] Duplicate identifiers are blocked
- [x] Unauthorized portfolio access is denied
- [x] Client lifecycle/version/archive tests pass
- [x] Full CI green — PR-BE-06 Backend CI run #44

---

## Head 3 — Staff, Capacity & Worklogs

**Head status: [x] COMPLETE**

- [x] **PR-BE-07 — Staff Master, Department, Designation & Reporting Line**
- [x] **PR-BE-08 — Attendance, Leave, Capacity, Assignment & Worklogs**

### Head 3 completion gate

- [x] Both PRs merged
- [x] Staff/workforce permission gates verified
- [x] Capacity calculations reconcile
- [x] Worklog totals and locks pass
- [x] Attendance and leave integrity tests pass
- [x] Full CI green — PR-BE-08 Backend CI run #50

---

## Head 4 — Engagement, Tasks & Operational Workflow

**Head status: [x] COMPLETE**

- [x] **PR-BE-09 — Engagement Core, Naming Series & Team Assignment**
- [x] **PR-BE-10 — Engagement Templates & Automatic Task Generation**
- [x] **PR-BE-11 — Task, Dependency, Deadline & Weighted Progress Engine**
- [x] **PR-BE-12 — Engagement Workflow, Review Queue & Final Closure Controls**

### Head 4 completion gate

- [x] All four PRs merged
- [x] One real engagement can be created and assigned
- [x] Template tasks generate correctly
- [x] Dependency and deadline rules pass
- [x] Weighted progress reconciles
- [x] Unauthorized closure/reopen attempts fail
- [x] Full CI green — PR-BE-12 Backend CI run #62

---

## Head 5 — Documents, Evidence & Working Papers

**Head status: [x] COMPLETE**

- [x] **PR-BE-13 — Private Document Storage, Metadata, Versioning & Access Logs**
- [x] **PR-BE-14 — Working Paper, Evidence Linkage, Review Notes & Sign-Off**

### Head 5 completion gate

- [x] Both PRs merged
- [x] Unauthorized document download is blocked
- [x] Document version history is retained
- [x] Working-paper sign-off sequence passes
- [x] Review-note resolution is traceable
- [x] Locked working papers cannot be silently edited
- [x] Full CI green — PR-BE-14 Backend CI run #68

---

## Head 6 — Audit Practice Engine

**Head status: [x] COMPLETE**

- [x] **PR-BE-15 — Audit Planning, Acceptance, Independence, Materiality & Risk**
- [x] **PR-BE-16 — Requisition, Testing, Issues, Completion & Finalization**

### Head 6 completion gate

- [x] Both PRs merged
- [x] Acceptance and independence gates pass
- [x] Risk-to-procedure linkage is complete
- [x] Requisition trail is traceable
- [x] Open high-risk issues block finalization
- [x] Complete audit file can be locked
- [x] Full CI green — PR-BE-16 Backend CI run #74

---

## Head 7 — Finance, Reporting & Production Hardening

**Head status: [ ] IN PROGRESS**

- [x] **PR-BE-17 — Fees, Invoices, Receipts, Expenses & Engagement Economics**
- [ ] **PR-BE-18 — Dashboards, Reports, Notifications, Backup & Production Hardening**

### Head 7 completion gate

- [ ] Both PRs merged
- [x] Invoice, receipt and outstanding balances reconcile
- [x] Engagement profitability reconciles
- [ ] Dashboard data matches source records
- [ ] Notification triggers pass
- [ ] Backup and restore test succeeds
- [ ] Production readiness audit passes
- [ ] Full CI green

---

# Overall Backend Completion Checklist

- [x] Head 1 — Platform Foundation & Security
- [x] Head 2 — Client Master & Relationship Management
- [x] Head 3 — Staff, Capacity & Worklogs
- [x] Head 4 — Engagement, Tasks & Operational Workflow
- [x] Head 5 — Documents, Evidence & Working Papers
- [x] Head 6 — Audit Practice Engine
- [ ] Head 7 — Finance, Reporting & Production Hardening

## Current phase

**Head 7 — Finance, Reporting & Production Hardening: IN PROGRESS**

Current implementation target: **PR-BE-18 — Dashboards, Reports, Notifications, Backup & Production Hardening**.
