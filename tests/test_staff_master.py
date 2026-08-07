from sqlalchemy import select
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.deps import require_password_changed
from app.main import app
from app.models import AuthUser
from app.staff_models import Department, Designation, StaffProfile, StaffSkill


def _admin_user() -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert user is not None
        db.expunge(user)
        return user


def test_staff_tables_registered():
    assert Department.__table__.name == "departments"
    assert Designation.__table__.name == "designations"
    assert StaffProfile.__table__.name == "staff_profiles"
    assert StaffSkill.__table__.name == "staff_skills"
    assert StaffProfile.__table__.c.staff_code.unique is True
    assert StaffProfile.__table__.c.auth_user_id.unique is True


def test_staff_api_create_hierarchy_search_and_version_control():
    app.dependency_overrides[require_password_changed] = _admin_user
    client = TestClient(app)
    try:
        dept = client.post("/api/v1/staff/departments", json={"code": "AUD", "name": "Audit"})
        assert dept.status_code in {201, 409}
        if dept.status_code == 409:
            with SessionLocal() as db:
                department = db.scalar(select(Department).where(Department.code == "AUD"))
                assert department is not None
                dept_id = department.id
        else:
            dept_id = dept.json()["id"]

        designation = client.post(
            "/api/v1/staff/designations",
            json={"code": "AUD-SR", "name": "Audit Senior", "department_id": dept_id, "rank_order": 30},
        )
        assert designation.status_code in {201, 409}
        if designation.status_code == 409:
            with SessionLocal() as db:
                row = db.scalar(select(Designation).where(Designation.code == "AUD-SR"))
                assert row is not None
                designation_id = row.id
        else:
            designation_id = designation.json()["id"]

        created = client.post(
            "/api/v1/staff",
            json={
                "full_name": "Staff Master Test User",
                "email": "staff-master-test@example.com",
                "department_id": dept_id,
                "designation_id": designation_id,
                "employment_type": "permanent",
                "skills": [{"skill_code": "AUDIT", "skill_name": "External Audit", "proficiency_level": "advanced"}],
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        staff_id = body["id"]
        assert body["staff_code"].startswith("FRC-STF-")
        assert body["version"] == 1
        assert body["employment_type"] == "PERMANENT"
        assert body["skills"][0]["skill_code"] == "AUDIT"

        listed = client.get("/api/v1/staff", params={"q": "Staff Master Test"})
        assert listed.status_code == 200
        assert any(item["id"] == staff_id for item in listed.json()["items"])

        updated = client.patch(
            f"/api/v1/staff/{staff_id}",
            json={"employment_status": "inactive", "expected_version": 1},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["employment_status"] == "INACTIVE"
        assert updated.json()["version"] == 2

        stale = client.patch(
            f"/api/v1/staff/{staff_id}",
            json={"phone": "000", "expected_version": 1},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "VERSION_CONFLICT"
    finally:
        app.dependency_overrides.clear()


def test_staff_self_supervision_rejected():
    app.dependency_overrides[require_password_changed] = _admin_user
    client = TestClient(app)
    try:
        created = client.post("/api/v1/staff", json={"full_name": "Self Supervisor Test"})
        assert created.status_code == 201, created.text
        staff_id = created.json()["id"]
        response = client.patch(
            f"/api/v1/staff/{staff_id}",
            json={"supervisor_staff_id": staff_id, "expected_version": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_SUPERVISOR"
    finally:
        app.dependency_overrides.clear()
