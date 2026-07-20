# FAMES & R Office PRO — Backend

FastAPI backend for FAMES & R Office PRO.

## Architecture & Infrastructure Lock

**Last updated:** 20 July 2026, 11:03 AM BDT (Asia/Dhaka)

The approved application infrastructure is:

- Frontend hosting: Vercel
- Backend API hosting: Render
- Primary relational database: PostgreSQL
- Document storage: Google Drive through the Google Drive API
- AI provider: Google Gemini API
- Authentication: Custom FastAPI JWT authentication
- API prefix: `/api/v1`

```text
Frontend (Vercel)
        |
        v
Backend API (Render)
        |-- PostgreSQL: structured application data
        |-- Google Drive API: documents and working files
        `-- Google Gemini API: controlled AI assistance
```

### PostgreSQL Storage Policy

PostgreSQL is the system of record for structured application data, including:

- Users, roles, permissions, and account status
- Staff and student profiles
- Departments and designations
- Clients, contacts, services, notes, and activity
- Jobs, engagements, assignments, tasks, deadlines, and status history
- Attendance, leave, work logs, and performance data
- Audit planning, risk, materiality, requisitions, review notes, and workflow records
- Notifications, activity logs, audit logs, and document metadata
- Google Drive file IDs, folder IDs, versions, ownership, and linked client or engagement references
- Controlled AI request metadata and audit history where retention is approved

PDF, Excel, Word, image, scan, and other binary documents must not be stored directly in PostgreSQL. These files belong in Google Drive; PostgreSQL stores only their metadata and relationships.

### Google Drive Storage Policy

Google Drive stores the actual office and client files, including:

- Client documents
- Audit working papers
- Financial statements
- Tax and VAT files
- PDF, Excel, and Word files
- Scanned documents and supporting evidence
- Generated reports approved for storage

Drive operations must be performed only through authenticated backend APIs. The frontend must not receive Google service-account credentials or unrestricted Drive credentials.

### Secret and API-Key Policy

The following secrets must be stored only in Render environment variables or an approved secret manager:

- PostgreSQL `DATABASE_URL`
- `JWT_SECRET`
- Google Drive credentials
- Google Gemini API key
- Production bootstrap credentials
- Email or other third-party service credentials

Gemini and Google Drive credentials must never be committed to GitHub, embedded in frontend code, or exposed through Vercel public environment variables. The frontend calls the FastAPI backend; the backend calls PostgreSQL, Google Drive, and Gemini.

### Current Development Direction

Authentication is treated as stable and must not be changed without a verified defect and regression proof. Development proceeds backend-first using the controlled batch roadmap below. Staff and student functionality remains part of Batch 7 under the locked sequence; it must not bypass unfinished prerequisite batches unless the project owner explicitly authorizes a roadmap change.

## Backend Technology Baseline

- Python FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Custom JWT authentication
- Server-side RBAC
- Render deployment
- API prefix: `/api/v1`

## Current Technical Setup

The backend owns authentication directly. Supabase Auth is not used or required for login.

Existing documented capabilities:

- Login ID + password authentication
- Argon2 password hashing
- JWT access tokens
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- Failed-login lockout
- Auth audit log
- Super Admin user creation and account status controls
- One-time environment-driven bootstrap script

> This section preserves the existing technical setup only. It does not mark any roadmap batch as complete, tested, audited, or approved.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

Health endpoints currently documented:

- `/health`
- `/api/v1/health`

The locked roadmap requires dedicated live and ready checks to be implemented and verified during Batch 1.

## Bootstrap First Users

Set only the password environment variables required for bootstrap, then run:

```bash
python -m scripts.bootstrap_users
```

Passwords must never be stored in source code. Each bootstrapped account must be forced to change its temporary password after first login.

## Production Requirements

Set a PostgreSQL `DATABASE_URL`, a strong random `JWT_SECRET`, and the allowed frontend origin or origins. Do not commit `.env`, passwords, tokens, database credentials, or production secrets.

---

# Backend Master Roadmap — 8 Controlled Batches

This is the locked implementation and approval plan for the FAMES & R Office PRO backend.

No backend implementation batch may begin until the project owner gives the required written instruction. Batch 1 must not start until the project owner explicitly says:

`START BATCH 1`

## README Control Table

| Batch | Name | Status | Progress | Audit Result | Approved By |
|------|------|------|------:|------|------|
| 1 | Recovery & Stabilization | IN PROGRESS | 0% | Pending | Pending |
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

**Current status:** `IN PROGRESS`

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

For every batch change, use this format without inventing history:

### Batch X — Date

- Status before:
- Status after:
- Commit/ZIP:
- Features completed:
- Tests executed:
- Audit result:
- Remaining blockers:
- Approved by:

### Roadmap Initialization

- Added controlled 8-batch backend roadmap
- No backend code changed
- All batches remain `NOT STARTED`
- Awaiting project owner approval to start Batch 1

### Batch 1 — July 19, 2026

- Status before: `NOT STARTED`
- Status after: `IN PROGRESS`
- Commit/ZIP: README status-start commit; backend ZIP pending
- Features completed: None; implementation has not started
- Tests executed: None
- Audit result: Pending
- Remaining blockers: Batch 1 implementation, test execution, evidence collection, and independent audit
- Approved by: Pending

### Architecture Lock — July 20, 2026, 11:03 AM BDT

- Locked Vercel as frontend hosting and Render as backend hosting.
- Locked PostgreSQL as the structured-data system of record.
- Locked Google Drive API for actual document storage; PostgreSQL stores document metadata only.
- Locked Google Gemini API behind the FastAPI backend.
- Confirmed that Gemini, Drive, database, and JWT secrets must remain backend-only environment variables.
- No application code, authentication behavior, database migration, or deployment configuration changed in this documentation commit.
