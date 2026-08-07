import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.deps import require_password_changed
from app.main import app
from app.models import AuthUser


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _admin_user() -> AuthUser:
    with SessionLocal() as db:
        user = db.scalar(select(AuthUser).where(AuthUser.login_id == "Admin@001"))
        assert user is not None
        db.expunge(user)
        return user


def _client() -> TestClient:
    app.dependency_overrides[require_password_changed] = _admin_user
    return TestClient(app)


def test_client_crud_search_activity_export_and_archive():
    admin = _admin_user()
    client = _client()
    headers = {"X-Correlation-ID": "test-client-api-001"}

    created = client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "legal_name": "API Contract Limited",
            "trading_name": "API Contract",
            "entity_type": "PRIVATE_LIMITED",
            "industry": "Technology",
            "partner_user_id": admin.id,
            "contacts": [{"full_name": "Primary Contact", "email": "contact@example.com", "is_primary": True}],
            "addresses": [{"line1": "1 Test Road", "city": "Dhaka", "is_primary": True}],
            "identifiers": [{"identifier_type": "TIN", "value": "API-TIN-001"}],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    client_id = body["id"]
    assert body["legal_name"] == "API Contract Limited"
    assert body["version"] == 1
    assert len(body["contacts"]) == 1
    assert len(body["addresses"]) == 1
    assert len(body["identifiers"]) == 1
    assert created.headers["x-correlation-id"] == "test-client-api-001"

    listed = client.get("/api/v1/clients", params={"q": "API Contract"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert any(item["id"] == client_id for item in listed.json()["items"])

    fetched = client.get(f"/api/v1/clients/{client_id}")
    assert fetched.status_code == 200
    assert fetched.json()["client_code"].startswith("FRC-CLI-")

    updated = client.patch(
        f"/api/v1/clients/{client_id}",
        json={"industry": "Professional Services", "expected_version": 1},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["industry"] == "Professional Services"
    assert updated.json()["version"] == 2

    stale = client.patch(
        f"/api/v1/clients/{client_id}",
        json={"industry": "Should Fail", "expected_version": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"

    activity = client.get(f"/api/v1/clients/{client_id}/activity")
    assert activity.status_code == 200
    event_types = {item["event_type"] for item in activity.json()}
    assert {"CLIENT_CREATED", "CLIENT_UPDATED"}.issubset(event_types)

    exported = client.get("/api/v1/clients/export")
    assert exported.status_code == 200
    assert "API Contract Limited" in exported.text

    archived = client.post(
        f"/api/v1/clients/{client_id}/archive",
        json={"reason": "Test archive", "expected_version": 2},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["is_archived"] is True
    assert archived.json()["version"] == 3

    default_list = client.get("/api/v1/clients", params={"q": "API Contract Limited"})
    assert all(item["id"] != client_id for item in default_list.json()["items"])


def test_duplicate_identifier_returns_conflict():
    admin = _admin_user()
    client = _client()

    first = client.post(
        "/api/v1/clients",
        json={
            "legal_name": "Duplicate One Limited",
            "entity_type": "PRIVATE_LIMITED",
            "partner_user_id": admin.id,
            "identifiers": [{"identifier_type": "BIN", "value": "BIN-API-999"}],
        },
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/clients",
        json={
            "legal_name": "Duplicate Two Limited",
            "entity_type": "PRIVATE_LIMITED",
            "partner_user_id": admin.id,
            "identifiers": [{"identifier_type": "BIN", "value": "BIN API 999"}],
        },
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CLIENT_DUPLICATE_IDENTIFIER"
