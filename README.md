# FAMES & R Office PRO — Backend

FastAPI backend for FAMES & R Office PRO.

## Architecture & Infrastructure Lock

**Last updated:** 20 July 2026, 11:13 AM BDT (Asia/Dhaka)

Approved infrastructure:

- Frontend hosting: Vercel
- Backend API hosting: Render
- Primary database: PostgreSQL
- Document storage: Google Drive API
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

## Storage Policy

### PostgreSQL

PostgreSQL is the system of record for structured application data:

- Users, roles, permissions, and account status
- Staff and article-student profiles
- Departments and designations
- Clients, contacts, services, notes, and activity
- Jobs, engagements, assignments, tasks, deadlines, and status history
- Attendance, leave, work logs, timesheets, and performance data
- Audit planning, risk, materiality, requisitions, review notes, and workflow records
- Notifications, activity logs, audit logs, and document metadata
- Google Drive file IDs, folder IDs, versions, ownership, and linked records
- Controlled AI request metadata and approved audit history

PDF, Excel, Word, image, scan, and other binary files must not be stored directly in PostgreSQL.

### Google Drive

Google Drive stores the actual files:

- Client documents
- Audit working papers
- Financial statements
- Tax and VAT files
- PDF, Excel, and Word files
- Scanned documents and supporting evidence
- Approved generated reports

The backend performs all Drive operations. The frontend must never receive Google service-account credentials or unrestricted Drive credentials.

## Secret and API-Key Policy

These secrets must stay only in Render environment variables or an approved secret manager:

- PostgreSQL `DATABASE_URL`
- `JWT_SECRET`
- Google Drive credentials
- Google Gemini API key
- Production bootstrap credentials
- Email and other third-party credentials

Secrets must never be committed to GitHub, embedded in frontend code, or exposed through public Vercel environment variables.

## Authentication Protection Rule

Login is currently treated as working and stable.

- Do not redesign or replace authentication without a verified defect.
- Preserve the locked FastAPI JWT contract.
- Any auth change requires regression proof for login, profile, refresh, logout, protected-route rejection, and re-login.
- Never remove or disable the owner's access without a tested recovery path.
- Never claim authentication is fixed without live evidence.

Locked endpoints:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

## Backend Technology Baseline

- Python FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Custom JWT authentication
- Argon2 password hashing
- Server-side RBAC
- Render deployment
- API prefix: `/api/v1`

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

---

# FAMES & R Office PRO — 12-Phase Master Roadmap

This roadmap is the approved review version for backend-first implementation. Only one phase may be active at a time unless the project owner explicitly authorizes non-conflicting parallel work.

## Roadmap Control Table

| Phase | Name | Status | Progress | Audit Result | Approved By |
|---|---|---|---:|---|---|
| 1 | Backend Stabilization | IN PROGRESS | 0% | Pending | Pending |
| 2 | Users, Staff & Students Foundation | NOT STARTED | 0% | Pending | Pending |
| 3 | Client Management | NOT STARTED | 0% | Pending | Pending |
| 4 | Engagement & Job Management | NOT STARTED | 0% | Pending | Pending |
| 5 | Staff Operations | NOT STARTED | 0% | Pending | Pending |
| 6 | Job Work Station | NOT STARTED | 0% | Pending | Pending |
| 7 | Audit Workflow | NOT STARTED | 0% | Pending | Pending |
| 8 | Google Drive Document Management | NOT STARTED | 0% | Pending | Pending |
| 9 | Notifications & Communication | NOT STARTED | 0% | Pending | Pending |
| 10 | Gemini AI Assistant | NOT STARTED | 0% | Pending | Pending |
| 11 | Dashboard & Reports | NOT STARTED | 0% | Pending | Pending |
| 12 | Production Hardening | NOT STARTED | 0% | Pending | Pending |

Allowed status values:

- `NOT STARTED`
- `IN PROGRESS`
- `BLOCKED`
- `READY FOR AUDIT`
- `CORRECTION REQUIRED`
- `APPROVED`

Only the project owner or an independent auditor may mark a phase `APPROVED`.

---

## Phase 1 — Backend Stabilization

### Scope

- Preserve the current working login/auth flow
- Verify PostgreSQL connectivity and persistence
- Verify Alembic migrations
- Validate CORS and production environment configuration
- Implement and verify `/health/live` and `/health/ready`
- Verify backup-admin and account-recovery procedures
- Review password-reset security
- Review foundational RBAC enforcement
- Run auth, RBAC, client, and database regression tests
- Remove secrets, caches, nested ZIPs, virtual environments, and generated junk

### Exit Criteria

- Current login remains working
- PostgreSQL persistence is proven
- Migration upgrade and rollback behavior is documented
- No insecure production defaults remain
- Recovery access is proven
- Required regression tests pass with evidence
- Independent audit approved

---

## Phase 2 — Users, Staff & Students Foundation

### Scope

- User account lifecycle
- Roles and permissions
- Role-permission mapping and overrides
- Staff profiles
- Article-student profiles
- Departments
- Designations
- Student batch or intake
- Manager and senior assignment
- Active and inactive status
- Unique employee and student IDs
- Basic activity log
- Last-active-Super-Admin protection

### Exit Criteria

- Users, staff, and students persist in PostgreSQL
- Server-side permissions are enforced
- Owner access cannot be accidentally removed
- Search, filtering, pagination, and validation work
- Independent audit approved

---

## Phase 3 — Client Management

### Scope

- Client master
- Contact persons
- Service types
- TIN, BIN, and RJSC information
- Client status
- Notes and confidentiality controls
- Client activity history
- Client 360 APIs
- Search, filtering, and pagination

### Exit Criteria

- Client data persists across refresh and deployment
- Confidential data follows role and assignment rules
- Client history and relationships are traceable
- Independent audit approved

---

## Phase 4 — Engagement & Job Management

### Scope

- Audit, Tax, VAT, and other engagement creation
- Financial year and reporting period
- Jobs and job assignments
- Staff and student team assignment
- Tasks and deadlines
- Budget hours
- Progress and controlled status workflow
- Status history and activity logs
- Search, filtering, and pagination
- Row-level and assignment-based access

### Exit Criteria

- Engagement and job lifecycle is persistent
- Invalid status transitions are blocked
- Team and assignment access rules are proven
- Student and technical-role restrictions are tested
- Independent audit approved

---

## Phase 5 — Staff Operations

### Scope

- Attendance
- Leave request and approval
- Daily work logs
- Timesheets
- Billable and non-billable hours
- Workload tracking
- Performance reviews
- Student training progress
- Competency checklist
- Salary and allowance foundation

### Exit Criteria

- Staff operations use persistent APIs
- Approval rules are enforced server-side
- Timesheet and workload totals are reproducible
- No simulated payroll or attendance success remains
- Independent audit approved

---

## Phase 6 — Job Work Station

Each engagement receives a controlled workspace containing:

- Overview
- Tasks
- Requisitions
- Documents
- Working papers
- Review notes
- Internal discussion
- Client message drafts
- Activity log

### Exit Criteria

- Every visible action maps to a real backend endpoint or is explicitly disabled
- Work Station data persists
- Internal and client-facing communications remain separated
- Review and approval restrictions are enforced
- No fake upload or fake send success exists
- Independent audit approved

---

## Phase 7 — Audit Workflow

### Scope

- Client acceptance
- Independence
- Engagement letter
- Audit planning
- Materiality
- Risk assessment
- Audit strategy
- Audit programme
- Substantive procedures
- Working-paper preparation
- Review and clearance
- Finalization
- Partner sign-off controls

### Exit Criteria

- Audit workflow is persistent and versioned
- Professional authority is separated from technical administration
- Review history and finalization evidence are retained
- Local-only approval and sign-off are prohibited
- Independent audit approved

---

## Phase 8 — Google Drive Document Management

### Scope

- Client-wise folder architecture
- Engagement-wise folder architecture
- Real file upload and download
- Google Drive file and folder ID persistence
- File versioning
- Replace and archive workflow
- Permission and destination control
- Document activity trail
- PostgreSQL metadata linkage

### Exit Criteria

- Actual files are stored in Google Drive
- PostgreSQL stores metadata and relationships only
- No fake upload success exists
- Permission, destination, and version rules are tested
- Independent audit approved

---

## Phase 9 — Notifications & Communication

### Scope

- Task deadline alerts
- Leave approval alerts
- Review-note alerts
- Missing-client-document alerts
- Internal notification center
- Unread counts
- Email draft, review, approval, and send workflow
- Delivery status
- Communication log and audit trail

### Exit Criteria

- Notifications come from real backend events
- Delivery status appears only after provider confirmation
- No fake email or message success exists
- Communication history is traceable
- Independent audit approved

---

## Phase 10 — Gemini AI Assistant

### Scope

- Document summaries
- Audit-risk suggestions
- Requisition drafts
- Review-note drafts
- Working-paper assistance
- Client-communication drafts
- Permission-aware context
- AI request and response audit trail
- Cost, rate, and retention controls

### Mandatory Restrictions

- AI cannot approve or sign professional work
- AI cannot bypass permissions
- AI cannot delete or execute restricted actions without authorized backend control
- AI output must be presented as assistance, not authoritative professional approval
- Gemini API key remains backend-only

### Exit Criteria

- AI scope and limitations are explicit
- AI actions are auditable
- Permission boundaries are tested
- Independent audit approved

---

## Phase 11 — Dashboard & Reports

### Scope

- Partner dashboard
- Manager dashboard
- Staff dashboard
- Student dashboard
- Client and engagement status
- Pending and overdue work
- Attendance and leave summaries
- Staff workload
- Billable hours
- Audit progress
- Office KPIs

### Exit Criteria

- Dashboard values come only from persistent backend data
- KPI calculations are documented and reproducible
- Role-based visibility is enforced
- No mock production metrics remain
- Independent audit approved

---

## Phase 12 — Production Hardening

### Scope

- Rate limiting
- Security headers
- Secret validation
- Database backup and restore test
- Migration verification
- Error monitoring
- Performance testing
- Dependency review
- API contract audit
- Full frontend/backend integration
- Render deployment verification
- Vercel deployment verification
- Final role-based end-to-end testing

### Mandatory Final Proof

```text
Owner/Admin
→ Login
→ Dashboard
→ Real profile and role visible
→ Refresh
→ Session remains valid
→ Logout
→ Protected route redirects to Login
→ Re-login
```

Module-level proof is required for:

- Users, roles, permissions, staff, and students
- Clients
- Engagements and jobs
- Staff operations
- Job Work Station
- Audit workflow
- Google Drive documents
- Notifications and communication
- Gemini AI restrictions
- Dashboards and reports

### Exit Criteria

- All critical tests pass
- Production deployments are verified
- Backup and restore are proven
- No unresolved P0 or P1 blockers remain
- No production screen converts backend failure into fake success
- Final independent audit approved

---

## Development Order

```text
Backend Stabilization
→ Users, Staff & Students
→ Clients
→ Engagements & Jobs
→ Staff Operations
→ Job Work Station
→ Audit Workflow
→ Google Drive
→ Notifications & Communication
→ Gemini AI
→ Dashboards & Reports
→ Production Hardening
```

## Phase Execution Rules

1. Only one phase may be active at a time unless the project owner explicitly authorizes otherwise.
2. A future phase must not begin before prerequisite data models and API contracts are stable.
3. Backend API contracts are the source of truth for frontend integration.
4. Every phase must include an implementation report, test evidence, API contract changes, migration list, and exact remaining gaps.
5. Never claim tests passed without actual command output.
6. Never claim deployment works without live evidence.
7. Never silently change an approved frontend/backend API contract.
8. Never commit passwords, tokens, API keys, database credentials, or other secrets.
9. Never present local, mock, or in-memory state as persistent production data.
10. Never convert backend failure into fake success.
11. Progress percentages must reflect verified work, not estimates.
12. `READY FOR AUDIT` is not complete until independent approval.
13. A failed audit must set the phase to `CORRECTION REQUIRED`.
14. Professional approval and sign-off must remain separate from technical administration.
15. Authentication changes require explicit defect evidence and complete regression proof.

## Change Log

### Roadmap Replacement — 20 July 2026, 11:13 AM BDT

- Replaced the previous eight-batch roadmap with the reviewed 12-phase master roadmap.
- Moved Users, Staff, and Students Foundation before Client and Engagement implementation.
- Separated Staff Operations, Google Drive, Notifications, Gemini AI, and Dashboards into dedicated phases.
- Preserved backend-first development and independent audit gates.
- Preserved the locked Vercel, Render, PostgreSQL, Google Drive, and Gemini architecture.
- Preserved the current authentication contract and added a strict owner-access protection rule.
- No application code, authentication logic, database migration, deployment configuration, or secret was changed in this documentation commit.
