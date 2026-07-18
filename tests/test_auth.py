import os

os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
os.environ["JWT_SECRET"] = "test-secret-that-is-definitely-long-enough-12345"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import AuthUser
from app.security import hash_password


client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add(AuthUser(login_id="Admin@001", email="admin@example.com", full_name="Admin", role="SUPER_ADMIN", password_hash=hash_password("StrongPass#123"), status="ACTIVE", must_change_password=True))
        db.commit()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("test_auth.db")
    except FileNotFoundError:
        pass


def test_login_and_me():
    response = client.post("/api/v1/auth/login", json={"login_id": "Admin@001", "password": "StrongPass#123", "remember_me": False})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["login_id"] == "Admin@001"
    assert me.json()["role"] == "SUPER_ADMIN"


def test_bad_password_rejected():
    response = client.post("/api/v1/auth/login", json={"login_id": "Admin@001", "password": "wrong"})
    assert response.status_code == 401
