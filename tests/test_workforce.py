from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.deps import require_password_changed
from app.main import app
from app.models import AuthUser
from app.staff_models import StaffProfile
from app.workforce_models import AttendanceRecord, CapacityAssignment, LeaveRecord, StaffWorklog


def _admin_user() -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert user is not None
        db.expunge(user)
        return user


def _staff_id() -> str:
    with SessionLocal() as db:
        existing = db.scalar(select(StaffProfile).where(StaffProfile.full_name == "Workforce Test User"))
        if existing:
            return existing.id
    app.dependency_overrides[require_password_changed] = _admin_user
    client = TestClient(app)
    created = client.post("/api/v1/staff", json={"full_name": "Workforce Test User"})
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_workforce_tables_registered():
    assert AttendanceRecord.__table__.name == "attendance_records"
    assert LeaveRecord.__table__.name == "leave_records"
    assert CapacityAssignment.__table__.name == "capacity_assignments"
    assert StaffWorklog.__table__.name == "staff_worklogs"


def test_attendance_leave_capacity_and_worklog_lock_flow():
    app.dependency_overrides[require_password_changed] = _admin_user
    client = TestClient(app)
    try:
        staff_id = _staff_id()
        work_date = date(2026, 8, 8).isoformat()

        attendance = client.post("/api/v1/workforce/attendance", json={"staff_id": staff_id, "work_date": work_date, "status": "present", "worked_minutes": 420})
        assert attendance.status_code in {201, 409}, attendance.text

        leave = client.post("/api/v1/workforce/leave", json={"staff_id": staff_id, "leave_date": work_date, "leave_type": "casual", "leave_minutes": 120, "status": "approved"})
        assert leave.status_code in {201, 409}, leave.text

        assignment = client.post("/api/v1/workforce/assignments", json={"staff_id": staff_id, "work_date": work_date, "source_type": "task", "source_id": "TASK-WF-001", "assigned_minutes": 240, "billable": True})
        assert assignment.status_code in {201, 409}, assignment.text

        worklog = client.post("/api/v1/workforce/worklogs", json={"staff_id": staff_id, "work_date": work_date, "resource_type": "task", "resource_id": "TASK-WF-001", "minutes": 180, "billable": True, "description": "Audit fieldwork"})
        assert worklog.status_code == 201, worklog.text
        worklog_id = worklog.json()["id"]
        assert worklog.json()["status"] == "DRAFT"
        assert worklog.json()["version"] == 1

        submitted = client.post(f"/api/v1/workforce/worklogs/{worklog_id}/submit", json={"expected_version": 1})
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "SUBMITTED"

        approved = client.post(f"/api/v1/workforce/worklogs/{worklog_id}/approve", json={"expected_version": 2})
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "APPROVED"

        locked = client.post(f"/api/v1/workforce/worklogs/{worklog_id}/lock", json={"expected_version": 3})
        assert locked.status_code == 200, locked.text
        assert locked.json()["status"] == "LOCKED"
        assert locked.json()["locked_at"] is not None

        invalid = client.post(f"/api/v1/workforce/worklogs/{worklog_id}/submit", json={"expected_version": 4})
        assert invalid.status_code == 409
        assert invalid.json()["error"]["code"] == "WORKLOG_TRANSITION_INVALID"

        capacity = client.get(f"/api/v1/workforce/capacity/{staff_id}", params={"work_date": work_date, "standard_minutes": 480})
        assert capacity.status_code == 200, capacity.text
        body = capacity.json()
        assert body["approved_leave_minutes"] == 120
        assert body["available_minutes"] == 360
        assert body["assigned_minutes"] == 240
        assert body["logged_minutes"] >= 180
        assert body["remaining_minutes"] == 120
    finally:
        app.dependency_overrides.clear()
