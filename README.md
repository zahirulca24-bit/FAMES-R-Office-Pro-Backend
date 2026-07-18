# FAMES & R Office PRO — Backend

FastAPI backend for FAMES & R Office PRO.

## Backend Technology Baseline

- Python FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Custom JWT authentication
- Server-side RBAC
- Render deployment
- API prefix: `/api/v1`

## Batch 1 Stabilized Technical Setup

- Frontend login contract preserved: `login_id`, `password`, `remember_me`
- Argon2 password hashing and versioned JWT session revocation
- Environment-only bootstrap credentials; no hardcoded runtime password
- Targeted Super Admin emergency recovery only
- Production configuration rejects SQLite, insecure JWT defaults, wildcard CORS, and localhost CORS
- Alembic adoption migration for pre-existing auth tables
- Process liveness: `GET /api/v1/health/live`
- Database/schema/migration readiness: `GET /api/v1/health/ready`
- Legacy health routes retained: `GET /health`, `GET /api/v1/health`
- Supabase Auth is not used

> Batch 1 is READY FOR AUDIT, not approved. Live Render deployment and live PostgreSQL persistence were not executed in this batch.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Bootstrap and Recovery

Normal bootstrap creates only missing configured users and never mutates an existing account:

```bash
python -m scripts.bootstrap_users
```

Emergency recovery is restricted to one configured `SUPER_ADMIN`. Set `BOOTSTRAP_FORCE_RESET=true`, set `BOOTSTRAP_RECOVERY_LOGIN_ID`, and provide only that account password environment variable. Remove or disable the recovery variables immediately after the single recovery run.

Passwords, tokens, database credentials, and production secrets must never be committed.

## Batch 1 Evidence Files

- `IMPLEMENTATION_REPORT.md`
- `TEST_REPORT.md`
- `API_CONTRACT.md`
- `MIGRATION_LIST.md`

---

# Backend Master Roadmap — 8 Controlled Batches

This is the locked implementation and approval plan for the FAMES & R Office PRO backend.

## README Control Table

| Batch | Name | Status | Progress | Audit Result | Approved By |
|------|------|------|------:|------|------|
| 1 | Recovery & Stabilization | READY FOR AUDIT | 95% | Pending | Pending |
| 2 | Users, RBAC & Clients | NOT STARTED | 0% | Pending | Pending |
| 3 | Jobs & Engagements | NOT STARTED | 0% | Pending | Pending |
| 4 | Work Station | NOT STARTED | 0% | Pending | Pending |
| 5 | Audit Engine | NOT STARTED | 0% | Pending | Pending |
| 6 | Drive & Communication | NOT STARTED | 0% | Pending | Pending |
| 7 | Staff, Notifications & AI | NOT STARTED | 0% | Pending | Pending |
| 8 | Production Hardening & E2E | NOT STARTED | 0% | Pending | Pending |

### Allowed Status Values

- `NOT STARTED`
- `IN PROGRESS`
- `BLOCKED`
- `READY FOR AUDIT`
- `CORRECTION REQUIRED`
- `APPROVED`

A backend engineer or implementation agent must not mark a batch `APPROVED`. Only the project owner or an independent auditor may approve a batch.

---

## Batch 1 — Recovery & Stabilization

### Scope

- Clean backend package
- Remove frontend files, `venv`, `node_modules`, nested ZIPs, caches, and secrets
- Preserve current working backend functionality
- Fix frontend authentication API contract
- Fix password-reset security
- Stabilize Admin bootstrap and recovery
- Verify PostgreSQL and Alembic
- Correct unsafe CORS and configuration
- Add `health/live` and `health/ready`
- Fix foundational RBAC security
- Run Auth, RBAC, Client, and Job regression tests

### Exit Criteria

- Clean backend-only ZIP
- Current frontend login contract preserved
- No hardcoded password
- No insecure production defaults
- Database persistence verified
- Required tests executed
- Independent audit approved

**Current status:** `READY FOR AUDIT`

---

## Batch 2 — Users, RBAC & Clients Completion

### Scope

- Complete user lifecycle management
- Roles
- Permissions
- Role-permission mapping
- Permission overrides
- Status controls
- Last-active-Super-Admin protection
- Admin password reset
- Client master
- Client contacts
- Client services
- Client notes
- Client activity
- Client 360 APIs
- Confidentiality controls

### Exit Criteria

- User and RBAC APIs complete
- Client APIs persistent
- Server-side permissions enforced
- Role-separation policy tested
- Independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch 3 — Jobs & Engagements

### Scope

- Engagements
- Jobs
- Job assignments
- Tasks
- Deadlines
- Status workflow
- Status history
- Activity logs
- Search, filter, and pagination
- Job overview
- Row-level access

### Exit Criteria

- Job lifecycle persistent
- Valid transitions enforced
- Assignment access tested
- Student and technical-role restrictions proven
- Independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch 4 — Work Station

### Scope

- Job Work Station overview
- Work Station sections
- Requisitions
- Requisition items
- Document metadata
- Working papers
- Working-paper version history
- Review notes
- Internal discussion
- Client message drafts
- Work Station activity
- Safe AI-context foundation only

### Exit Criteria

- Work Station APIs complete
- No fake uploads
- No fake email sending
- Review and approval restrictions enforced
- Independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch 5 — Audit Engine

### Scope

- Audit planning
- Client acceptance
- Independence
- Engagement letter
- Materiality
- Risk assessment
- Audit strategy
- Audit programme
- Substantive procedures
- Working-paper review
- Review issues
- Finalization
- Professional sign-off rules

### Exit Criteria

- Audit workflow persistent
- Professional authority separated from technical admin
- Review and finalization controls tested
- Independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch 6 — Google Drive & Communication

### Scope

- Google Drive folder architecture
- File metadata
- Folder and file ID persistence
- File upload and download integration
- Version tracking
- Client communications
- Internal communication
- Email integration
- Draft, review, approve, and send workflow
- Communication audit trail

### Exit Criteria

- Real Drive operations proven
- No fake upload success
- No fake email success
- Permission and destination rules tested
- Independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch 7 — Staff, Notifications & AI

### Scope

- Staff profiles
- Attendance
- Leave
- Work logs
- Performance
- Salary and allowance foundation
- Notification engine
- Deadline alerts
- Review alerts
- Client-document alerts
- Permission-aware AI context
- Controlled AI suggestions and actions

### Exit Criteria

- Staff operations persistent
- Notification triggers tested
- AI cannot bypass permissions
- AI cannot approve or sign professional work
- Independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch 8 — Production Hardening & Final E2E

### Scope

- Rate limiting
- Security headers
- Secret validation
- Audit logging
- Error monitoring
- Database backup
- Restore testing
- Migration verification
- Performance checks
- Dependency review
- API contract audit
- Render deployment
- Frontend and backend integration
- Final end-to-end verification

### Mandatory Final Proof

`Admin@001`  
→ Login  
→ Dashboard  
→ Refresh  
→ Logout  
→ Re-login

Module-level proof is also mandatory for:

- Users and RBAC
- Clients
- Jobs
- Work Station
- Audit
- Drive
- Communication
- Staff
- Notifications
- AI restrictions

### Exit Criteria

- All critical tests pass
- Production deployment verified
- No unresolved P0 or P1 blockers
- Final independent audit approved

**Initial status:** `NOT STARTED`

---

## Batch Execution Rules

1. Only one batch may be active at a time.
2. No future batch may begin before the current batch is independently audited and approved.
3. Every batch must return one clean backend-only ZIP.
4. Every batch must include:
   - `IMPLEMENTATION_REPORT.md`
   - `TEST_REPORT.md`
   - `API_CONTRACT.md` or updated API documentation
   - Migration list
   - Exact remaining gaps
5. Never claim tests passed without actual command output.
6. Never claim deployment works without live evidence.
7. Never silently change the frontend API contract.
8. Never use Supabase Auth.
9. Never commit passwords, tokens, database credentials, or other secrets.
10. Never include frontend source, `venv`, `node_modules`, caches, nested ZIPs, or generated junk in the backend ZIP.
11. The README progress percentage must reflect actual verified work, not estimates or optimistic claims.
12. A batch at `READY FOR AUDIT` is not complete until audit approval.
13. Any failed audit must set the batch to `CORRECTION REQUIRED`.
14. Code from a later batch must not be mixed into an earlier batch without explicit written approval.

---

## Backend Batch Change Log

### Roadmap Initialization

- Added controlled 8-batch backend roadmap
- No backend code changed
- All batches remained `NOT STARTED`
- Awaited project owner approval to start Batch 1

### Batch 1 — July 19, 2026

- Status before: `NOT STARTED`
- Status after: `READY FOR AUDIT`
- Commit/ZIP: branch `batch-1-recovery-stabilization`; clean ZIP `FAMES-R-Office-Pro-Backend-Batch-1-READY-FOR-AUDIT.zip`; final commit SHA supplied with delivery
- Features completed: recovery and bootstrap stabilization, frontend auth contract preservation, password/session security, production configuration validation, Alembic adoption baseline, live/ready health checks, foundational RBAC hardening, clean backend packaging, and evidence documentation
- Tests executed: clean editable install, dependency check, 20 automated tests, Python compilation, SQLite migration upgrade/current verification, legacy database adoption test, PostgreSQL offline migration compilation, API route inventory, secret/junk scan, and ZIP manifest verification
- Audit result: Pending independent audit
- Remaining blockers: independent audit approval; live PostgreSQL persistence and Render deployment were not executed; Client and Job modules do not yet exist and remain locked to Batches 2 and 3
- Approved by: Pending
