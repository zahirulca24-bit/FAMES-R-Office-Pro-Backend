import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.client_models import Client
from app.db import SessionLocal
from app.deps import require_password_changed
from app.engagement_models import Engagement
from app.engagement_template_models import EngagementGeneratedTask, EngagementRequiredDocument, EngagementTemplate
from app.main import app
from app.models import AuthUser


def _admin_user() -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert user is not None
        db.expunge(user)
        return user


def _engagement() -> Engagement:
    admin = _admin_user()
    token = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        client = Client(
            client_code=f"TPL-{token}",
            legal_name=f"Template Test {token}",
            entity_type="PRIVATE_LIMITED",
            status="ACTIVE",
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        db.add(client)
        db.flush()
        engagement = Engagement(
            engagement_code=f"FRC-ENG-2099-{uuid.uuid4().int % 999999:06d}",
            client_id=client.id,
            service_type="STATUTORY_AUDIT",
            title="Template Generation Test",
            period_start=date(2026, 7, 1),
            period_end=date(2027, 6, 30),
            partner_user_id=admin.id,
            deadline=date(2027, 9, 30),
            created_by_user_id=admin.id,
            updated_by_user_id=admin.id,
        )
        db.add(engagement)
        db.commit()
        db.refresh(engagement)
        db.expunge(engagement)
        return engagement


def test_template_tables_registered():
    assert EngagementTemplate.__table__.name == "engagement_templates"
    assert EngagementGeneratedTask.__table__.name == "engagement_generated_tasks"
    assert EngagementRequiredDocument.__table__.name == "engagement_required_documents"


def test_create_and_apply_template_generates_tasks_documents_and_deadlines():
    app.dependency_overrides[require_password_changed] = _admin_user
    client = TestClient(app)
    try:
        engagement = _engagement()
        code = f"AUD-{uuid.uuid4().hex[:6].upper()}"
        created = client.post(
            "/api/v1/engagement-templates",
            json={
                "code": code,
                "name": "Statutory Audit Standard",
                "service_type": "statutory_audit",
                "tasks": [
                    {"task_code": "PLAN", "title": "Audit Planning", "stage": "planning", "sequence": 10, "due_offset_days": 3, "default_assignment_role": "MANAGER", "approval_role": "PARTNER"},
                    {"task_code": "FIELD", "title": "Fieldwork", "stage": "fieldwork", "sequence": 20, "due_offset_days": 10},
                ],
                "required_documents": [
                    {"document_code": "FS", "title": "Draft Financial Statements", "stage": "planning", "required": True}
                ],
            },
        )
        assert created.status_code == 201, created.text
        template_id = created.json()["id"]

        applied = client.post(
            f"/api/v1/engagement-templates/engagements/{engagement.id}/apply",
            json={"template_id": template_id, "expected_engagement_version": 1, "anchor_date": "2026-08-01"},
        )
        assert applied.status_code == 200, applied.text
        body = applied.json()
        assert len(body["generated_tasks"]) == 2
        assert body["generated_tasks"][0]["task_code"] == "PLAN"
        assert body["generated_tasks"][0]["due_date"] == "2026-08-04"
        assert body["generated_tasks"][0]["approval_role"] == "PARTNER"
        assert len(body["required_documents"]) == 1

        duplicate = client.post(
            f"/api/v1/engagement-templates/engagements/{engagement.id}/apply",
            json={"template_id": template_id, "expected_engagement_version": 2, "anchor_date": "2026-08-01"},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "ENGAGEMENT_TEMPLATE_ALREADY_APPLIED"

        listed = client.get(f"/api/v1/engagement-templates/engagements/{engagement.id}/tasks")
        assert listed.status_code == 200
        assert [x["task_code"] for x in listed.json()] == ["PLAN", "FIELD"]
    finally:
        app.dependency_overrides.clear()
