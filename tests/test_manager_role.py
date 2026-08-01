from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _login(login_id: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"login_id": login_id, "password": password, "remember_me": False},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_manager_forced_password_change_and_token_revocation():
    old_token = _login("Manager@001", "ManagerPass#123")
    headers = {"Authorization": f"Bearer {old_token}"}

    blocked = client.get("/api/v1/manager/access-check", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Password change required"

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "ManagerPass#123", "new_password": "ManagerNewPass#456"},
    )
    assert changed.status_code == 200, changed.text

    revoked = client.get("/api/v1/auth/me", headers=headers)
    assert revoked.status_code == 401
    assert revoked.json()["detail"] == "Session is no longer valid"

    new_token = _login("Manager@001", "ManagerNewPass#456")
    manager_headers = {"Authorization": f"Bearer {new_token}"}
    allowed = client.get("/api/v1/manager/access-check", headers=manager_headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["role"] == "MANAGER"

    admin_denied = client.post(
        "/api/v1/admin/users",
        headers=manager_headers,
        json={
            "login_id": "Manager@999",
            "email": "manager999@example.com",
            "full_name": "Unauthorized Manager",
            "role": "MANAGER",
            "password": "Unauthorized#123",
        },
    )
    assert admin_denied.status_code == 403


def test_student_cannot_use_manager_endpoint():
    token = _login("Student@001", "StudentPass#123")
    response = client.get(
        "/api/v1/manager/access-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Manager access required"
