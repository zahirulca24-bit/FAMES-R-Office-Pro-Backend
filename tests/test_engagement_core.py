from sqlalchemy import select
from fastapi.testclient import TestClient

from app.client_models import Client
from app.db import SessionLocal
from app.deps import require_password_changed
from app.engagement_models import Engagement, EngagementNumberSequence, EngagementTeamMember
from app.main import app
from app.models import AuthUser


def _admin_user() -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert user is not None
        db.expunge(user)
        return user


def _client() -> TestClient:
    app.dependency_overrides[require_password_changed] = _admin_user
    return TestClient(app)


def _active_client(client: TestClient, admin: AuthUser, suffix: str) -> str:
    created = client.post(
        "/api/v1/clients",
        json={
            "legal_name": f"Engagement Test Client {suffix}",
            "entity_type": "PRIVATE_LIMITED",
            "partner_user_id": admin.id,
        },
    )
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    with SessionLocal() as db:
        row = db.get(Client, client_id)
        assert row is not None
        row.status = "ACTIVE"
        db.commit()
    return client_id


def test_engagement_tables_registered():
    assert Engagement.__table__.name == "engagements"
    assert EngagementTeamMember.__table__.name == "engagement_team_members"
    assert EngagementNumberSequence.__table__.name == "engagement_number_sequences"
    assert Engagement.__table__.c.engagement_code.unique is True


def test_engagement_create_search_update_and_team_assignment():
    admin = _admin_user()
    client = _client()
    try:
        client_id = _active_client(client, admin, "A")
        staff = client.post(
            "/api/v1/staff",
            json={"full_name": "Engagement Assigned Staff", "employment_type": "PERMANENT"},
        )
        assert staff.status_code == 201, staff.text
        staff_id = staff.json()["id"]

        created = client.post(
            "/api/v1/engagements",
            json={
                "client_id": client_id,
                "service_type": "statutory_audit",
                "title": "FY 2025-2026 Statutory Audit",
                "partner_user_id": admin.id,
                "priority": "high",
                "fee_currency": "bdt",
                "agreed_fee_minor": 12500000,
                "budget_minutes": 12000,
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        engagement_id = body["id"]
        assert body["engagement_code"].startswith("FRC-ENG-")
        assert body["service_type"] == "STATUTORY_AUDIT"
        assert body["priority"] == "HIGH"
        assert body["version"] == 1

        listed = client.get("/api/v1/engagements", params={"q": "FY 2025-2026"})
        assert listed.status_code == 200, listed.text
        assert any(item["id"] == engagement_id for item in listed.json()["items"])

        assigned = client.post(
            f"/api/v1/engagements/{engagement_id}/team",
            json={"staff_id": staff_id, "assignment_role": "reviewer"},
        )
        assert assigned.status_code == 201, assigned.text
        assert assigned.json()["assignment_role"] == "REVIEWER"

        fetched = client.get(f"/api/v1/engagements/{engagement_id}")
        assert fetched.status_code == 200
        assert any(item["staff_id"] == staff_id for item in fetched.json()["team"])

        updated = client.patch(
            f"/api/v1/engagements/{engagement_id}",
            json={"priority": "urgent", "budget_minutes": 13000, "expected_version": 1},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["priority"] == "URGENT"
        assert updated.json()["budget_minutes"] == 13000
        assert updated.json()["version"] == 2

        stale = client.patch(
            f"/api/v1/engagements/{engagement_id}",
            json={"title": "Stale update", "expected_version": 1},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "VERSION_CONFLICT"
    finally:
        app.dependency_overrides.clear()


def test_engagement_rejects_unready_client_and_unauthorized_creator():
    admin = _admin_user()
    client = _client()
    try:
        prospect = client.post(
            "/api/v1/clients",
            json={
                "legal_name": "Prospect Engagement Block Test",
                "entity_type": "PRIVATE_LIMITED",
                "partner_user_id": admin.id,
            },
        )
        assert prospect.status_code == 201
        blocked = client.post(
            "/api/v1/engagements",
            json={
                "client_id": prospect.json()["id"],
                "service_type": "TAX_RETURN",
                "title": "Blocked Prospect Engagement",
                "partner_user_id": admin.id,
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "CLIENT_NOT_READY_FOR_ENGAGEMENT"

        student = _admin_user()
        student.role = "STUDENT"
        app.dependency_overrides[require_password_changed] = lambda: student
        denied = client.post(
            "/api/v1/engagements",
            json={
                "client_id": prospect.json()["id"],
                "service_type": "TAX_RETURN",
                "title": "Unauthorized Engagement",
                "partner_user_id": admin.id,
            },
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "PERMISSION_DENIED"
    finally:
        app.dependency_overrides.clear()
