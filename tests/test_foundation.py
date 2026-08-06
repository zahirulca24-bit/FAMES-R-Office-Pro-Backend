from fastapi.testclient import TestClient

from app.foundation.access import AccessContext, evaluate_access
from app.foundation.permissions import Permission, role_has_permission
from app.foundation.records import RecordState, format_record_code
from app.main import app


def test_permission_catalogue_is_deny_by_default() -> None:
    assert role_has_permission("SUPER_ADMIN", Permission.CLIENT_CREATE)
    assert not role_has_permission("UNKNOWN", Permission.CLIENT_VIEW)
    assert not role_has_permission("STAFF", Permission.ADMIN_USER_MANAGE)


def test_access_requires_record_scope_for_non_super_admin() -> None:
    denied = evaluate_access(
        AccessContext(
            user_id="u1",
            role="MANAGER",
            permission=Permission.CLIENT_VIEW,
        )
    )
    allowed = evaluate_access(
        AccessContext(
            user_id="u1",
            role="MANAGER",
            permission=Permission.CLIENT_VIEW,
            portfolio_authorized=True,
        )
    )
    assert not denied.allowed
    assert denied.reason == "RECORD_SCOPE_DENIED"
    assert allowed.allowed


def test_record_code_and_archive_versioning() -> None:
    assert format_record_code("cli", 42) == "CLI-000042"
    state = RecordState()
    archived = state.archive(actor_id="admin")
    assert archived.is_archived
    assert archived.version == 2
    assert archived.archived_by == "admin"


def test_correlation_id_is_returned() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live", headers={"X-Correlation-ID": "test-request-1"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "test-request-1"
