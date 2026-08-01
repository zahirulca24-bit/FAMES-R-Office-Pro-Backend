from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_and_me():
    response = client.post(
        "/api/v1/auth/login",
        json={"login_id": "Admin@001", "password": "StrongPass#123", "remember_me": False},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["login_id"] == "Admin@001"
    assert me.json()["role"] == "SUPER_ADMIN"


def test_bad_password_rejected():
    response = client.post(
        "/api/v1/auth/login",
        json={"login_id": "Admin@001", "password": "wrong"},
    )
    assert response.status_code == 401
