import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import SessionLocal
from app.deps import require_password_changed
from app.main import app
from app.models import AuthUser
from app.operations_models import BackupVerification, NotificationEvent, ProductionReadinessCheck


def _super_admin() -> AuthUser:
    return AuthUser(
        id="test-ops-super-admin",
        login_id="ops-super-admin",
        full_name="Operations Super Admin",
        role="SUPER_ADMIN",
        password_hash="x",
        status="ACTIVE",
        must_change_password=False,
    )


def test_operations_models_registered():
    assert NotificationEvent.__table__.name == "notification_events"
    assert BackupVerification.__table__.name == "backup_verifications"
    assert ProductionReadinessCheck.__table__.name == "production_readiness_checks"


def test_notification_backup_readiness_and_dashboard_flow():
    suffix = uuid.uuid4().hex[:8].upper()
    event_key = f"TEST_EVENT_{suffix}"
    backup_ref = f"backup-{suffix}"
    check_key = f"API_HEALTH_{suffix}"

    app.dependency_overrides[require_password_changed] = _super_admin
    http = TestClient(app)
    try:
        notification = http.post(
            "/api/v1/operations/notifications",
            json={
                "event_key": event_key,
                "resource_type": "SYSTEM",
                "resource_id": suffix,
                "subject": "Operational notification",
                "body": "Verification event",
                "channel": "IN_APP",
            },
        )
        assert notification.status_code == 201, notification.text
        notification_id = notification.json()["id"]
        assert notification.json()["status"] == "PENDING"

        delivered = http.post(f"/api/v1/operations/notifications/{notification_id}/deliver")
        assert delivered.status_code == 200, delivered.text
        assert delivered.json()["status"] == "DELIVERED"

        readiness_before = http.get("/api/v1/operations/production-readiness")
        assert readiness_before.status_code == 200, readiness_before.text
        assert readiness_before.json()["ready"] is False

        check = http.put(
            "/api/v1/operations/readiness-checks",
            json={"check_key": check_key, "passed": True, "evidence": "CI and health verification"},
        )
        assert check.status_code == 200, check.text
        assert check.json()["passed"] is True

        backup = http.post(
            "/api/v1/operations/backup-verifications",
            json={
                "backup_reference": backup_ref,
                "backup_status": "SUCCESS",
                "restore_test_status": "SUCCESS",
                "notes": "Isolated restore verification",
            },
        )
        assert backup.status_code == 201, backup.text

        readiness = http.get("/api/v1/operations/production-readiness")
        assert readiness.status_code == 200, readiness.text
        body = readiness.json()
        assert body["backup_restore_verified"] is True
        assert body["checks_total"] >= 1
        assert body["checks_passed"] >= 1

        dashboard = http.get("/api/v1/operations/dashboard")
        assert dashboard.status_code == 200, dashboard.text
        dash = dashboard.json()
        assert dash["approved_invoices_minor"] >= dash["receipts_minor"] or dash["outstanding_minor"] == 0
        assert "active_clients" in dash
        assert "open_audit_issues" in dash
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            db.execute(delete(NotificationEvent).where(NotificationEvent.event_key == event_key))
            db.execute(delete(BackupVerification).where(BackupVerification.backup_reference == backup_ref))
            db.execute(delete(ProductionReadinessCheck).where(ProductionReadinessCheck.check_key == check_key))
            db.commit()
