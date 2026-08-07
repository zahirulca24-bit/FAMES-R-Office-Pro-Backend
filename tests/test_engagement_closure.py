import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.client_models import Client
from app.db import SessionLocal
from app.deps import require_password_changed
from app.engagement_closure_models import EngagementReviewAction
from app.engagement_models import Engagement
from app.main import app
from app.models import AuthUser
from app.workflow_models import RecordLock


def _admin_user() -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert user is not None
        db.expunge(user)
        return user


def _new_engagement() -> tuple[str, int]:
    suffix = uuid.uuid4().hex[:8].upper()
    with SessionLocal() as db:
        admin = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert admin is not None
        client = Client(
            client_code=f"CL-WF-{suffix}",
            legal_name=f"Workflow Test {suffix}",
            entity_type="PRIVATE_LIMITED",
            status="ACTIVE",
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        db.add(client)
        db.flush()
        engagement = Engagement(
            engagement_code=f"FRC-ENG-WF-{suffix}",
            client_id=client.id,
            service_type="AUDIT",
            title="Closure workflow test",
            partner_user_id=admin.id,
            status="IN_PROGRESS",
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        db.add(engagement)
        db.commit()
        return engagement.id, engagement.version


def test_review_action_table_registered():
    assert EngagementReviewAction.__table__.name == "engagement_review_actions"


def test_engagement_review_close_lock_and_reopen_revision():
    engagement_id, version = _new_engagement()
    app.dependency_overrides[require_password_changed] = _admin_user
    client = TestClient(app)
    try:
        submitted = client.post(
            f"/api/v1/engagement-workflow/{engagement_id}/submit-review",
            json={"expected_version": version, "reason": "Work completed"},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "UNDER_REVIEW"

        approved = client.post(
            f"/api/v1/engagement-workflow/{engagement_id}/approve",
            json={"expected_version": submitted.json()["version"], "reason": "Review complete"},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "READY_TO_CLOSE"

        closed = client.post(
            f"/api/v1/engagement-workflow/{engagement_id}/close",
            json={"expected_version": approved.json()["version"], "reason": "Partner final closure"},
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == "CLOSED"
        assert closed.json()["lock_state"] == "LOCKED"
        assert closed.json()["revision_number"] == 1

        reopened = client.post(
            f"/api/v1/engagement-workflow/{engagement_id}/reopen",
            json={"expected_version": closed.json()["version"], "reason": "Post-closure correction required"},
        )
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["status"] == "REOPENED"
        assert reopened.json()["lock_state"] == "OPEN"
        assert reopened.json()["revision_number"] == 2

        history = client.get(f"/api/v1/engagement-workflow/{engagement_id}/history")
        assert history.status_code == 200
        actions = [row["action_type"] for row in history.json()]
        assert actions == [
            "ENGAGEMENT_SUBMITTED_FOR_REVIEW",
            "ENGAGEMENT_REVIEW_APPROVED",
            "ENGAGEMENT_CLOSED",
            "ENGAGEMENT_REOPENED",
        ]

        with SessionLocal() as db:
            lock = db.scalar(
                select(RecordLock).where(
                    RecordLock.resource_type == "ENGAGEMENT",
                    RecordLock.resource_id == engagement_id,
                )
            )
            assert lock is not None
            assert lock.state == "OPEN"
            assert lock.revision_number == 2
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_close_engagement():
    engagement_id, _ = _new_engagement()
    with SessionLocal() as db:
        engagement = db.get(Engagement, engagement_id)
        assert engagement is not None
        engagement.status = "READY_TO_CLOSE"
        staff_user = AuthUser(
            login_id=f"staff-wf-{uuid.uuid4().hex[:8]}",
            full_name="Workflow Staff",
            role="STAFF",
            password_hash="not-used",
            status="ACTIVE",
            must_change_password=False,
        )
        db.add(staff_user)
        db.commit()
        db.refresh(staff_user)
        db.expunge(staff_user)

    app.dependency_overrides[require_password_changed] = lambda: staff_user
    client = TestClient(app)
    try:
        response = client.post(
            f"/api/v1/engagement-workflow/{engagement_id}/close",
            json={"expected_version": 1, "reason": "Unauthorized close attempt"},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"
    finally:
        app.dependency_overrides.clear()
