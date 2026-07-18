import importlib
import os
from pathlib import Path

TEST_DB = Path("test_batch1.db").resolve()
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "batch1-test-secret-that-is-long-enough-2026"
os.environ["JWT_ISSUER"] = "fames-r-office-pro"
os.environ["JWT_AUDIENCE"] = "fames-r-office-pro-frontend"
os.environ["CORS_ORIGINS"] = "https://fames-r-office-pro-frontend.vercel.app,http://localhost:5173"
os.environ["LOGIN_MAX_FAILURES"] = "3"
os.environ["LOGIN_LOCK_MINUTES"] = "15"

from alembic import command
from alembic.config import Config

command.upgrade(Config("alembic.ini"), "head")

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete, text

from app.config import Settings
from app.db import SessionLocal, engine
from app.main import app

app_main_module = importlib.import_module("app.main")
from app.models import AuthAuditLog, AuthUser
from app.security import hash_password, verify_password
from scripts.bootstrap_users import main as bootstrap_users


client = TestClient(app)


def _create_user(
    login_id: str,
    password: str,
    *,
    role: str = "STUDENT",
    status: str = "ACTIVE",
    must_change_password: bool = False,
    email: str | None = None,
) -> AuthUser:
    with SessionLocal() as db:
        user = AuthUser(
            login_id=login_id,
            email=email,
            full_name=login_id,
            role=role,
            password_hash=hash_password(password),
            status=status,
            must_change_password=must_change_password,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def _login(login_id: str, password: str, remember_me: bool = False):
    return client.post(
        "/api/v1/auth/login",
        json={"login_id": login_id, "password": password, "remember_me": remember_me},
    )


def setup_function():
    for key in (
        "BOOTSTRAP_ADMIN_PASSWORD",
        "BOOTSTRAP_MANAGER_PASSWORD",
        "BOOTSTRAP_FORCE_RESET",
        "BOOTSTRAP_RECOVERY_LOGIN_ID",
    ):
        os.environ.pop(key, None)
    with SessionLocal() as db:
        db.execute(delete(AuthAuditLog))
        db.execute(delete(AuthUser))
        db.commit()


def teardown_module():
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


def test_live_and_legacy_health_contracts():
    for path in ("/health", "/api/v1/health", "/api/v1/health/live"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_ready_health_verifies_database_schema_and_migration():
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "schema": "ok", "migration": "ok"},
    }


def test_ready_health_reports_startup_bootstrap_failure_without_breaking_liveness():
    app_main_module._startup_bootstrap_error = "bootstrap error: RuntimeError"
    try:
        assert client.get("/api/v1/health/live").status_code == 200
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json()["detail"]["checks"]["startup"] == "bootstrap error: RuntimeError"
    finally:
        app_main_module._startup_bootstrap_error = None


def test_frontend_login_contract_and_me_are_preserved():
    _create_user("Admin@001", "StrongPass#123", role="SUPER_ADMIN", email="admin@example.com")
    response = _login(" Admin@001 ", "StrongPass#123", remember_me=True)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"access_token", "token_type", "expires_in", "user"}
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 43_200 * 60
    assert payload["user"]["login_id"] == "Admin@001"
    assert payload["user"]["full_name"] == "Admin@001"
    assert payload["user"]["must_change_password"] is False

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["role"] == "SUPER_ADMIN"


def test_login_rejects_unknown_or_wrong_credentials():
    _create_user("Student@001", "StrongPass#123")
    unknown = _login("Unknown@001", "StrongPass#123")
    wrong = _login("Student@001", "wrong")
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"] == "Invalid login ID or password"


def test_login_lockout_blocks_correct_password_after_threshold():
    _create_user("Student@001", "StrongPass#123")
    for _ in range(3):
        assert _login("Student@001", "wrong").status_code == 401
    locked = _login("Student@001", "StrongPass#123")
    assert locked.status_code == 423


def test_password_change_revokes_existing_token_and_requires_relogin():
    _create_user("Manager@001", "OldStrong#123", role="MANAGER")
    login = _login("Manager@001", "OldStrong#123")
    token = login.json()["access_token"]

    changed = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "OldStrong#123", "new_password": "NewStrong#456"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["reauthentication_required"] is True

    old_session = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert old_session.status_code == 401
    assert _login("Manager@001", "OldStrong#123").status_code == 401
    assert _login("Manager@001", "NewStrong#456").status_code == 200


def test_forced_password_change_blocks_privileged_admin_operation():
    _create_user(
        "Admin@001",
        "StrongPass#123",
        role="SUPER_ADMIN",
        must_change_password=True,
    )
    token = _login("Admin@001", "StrongPass#123").json()["access_token"]
    response = client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "login_id": "Student@009",
            "email": "student9@example.com",
            "full_name": "Student Nine",
            "role": "STUDENT",
            "password": "StudentPass#123",
        },
    )
    assert response.status_code == 403
    assert "Password change required" in response.json()["detail"]


def test_non_super_admin_cannot_use_admin_api():
    _create_user("Manager@001", "StrongPass#123", role="MANAGER")
    token = _login("Manager@001", "StrongPass#123").json()["access_token"]
    response = client.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "login_id": "Student@009",
            "email": "student9@example.com",
            "full_name": "Student Nine",
            "role": "STUDENT",
            "password": "StudentPass#123",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Super Admin access required"


def test_super_admin_can_create_user_and_duplicate_identity_is_rejected():
    _create_user("Admin@001", "StrongPass#123", role="SUPER_ADMIN")
    token = _login("Admin@001", "StrongPass#123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "login_id": "Student@009",
        "email": "student9@example.com",
        "full_name": "Student Nine",
        "role": "student",
        "password": "StudentPass#123",
    }
    created = client.post("/api/v1/admin/users", headers=headers, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "STUDENT"

    duplicate_login = client.post("/api/v1/admin/users", headers=headers, json=body)
    assert duplicate_login.status_code == 409

    body["login_id"] = "Student@010"
    duplicate_email = client.post("/api/v1/admin/users", headers=headers, json=body)
    assert duplicate_email.status_code == 409


def test_super_admin_cannot_disable_own_account():
    _create_user("Admin@001", "StrongPass#123", role="SUPER_ADMIN")
    token = _login("Admin@001", "StrongPass#123").json()["access_token"]
    response = client.patch(
        "/api/v1/admin/users/Admin@001/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "DISABLED"},
    )
    assert response.status_code == 400


def test_bootstrap_is_idempotent_and_does_not_reactivate_or_reset_existing_user():
    _create_user(
        "Admin@001",
        "OriginalPass#123",
        role="SUPER_ADMIN",
        status="SUSPENDED",
        must_change_password=False,
        email="admin@example.com",
    )
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "DifferentPass#456"
    bootstrap_users()

    with SessionLocal() as db:
        user = db.query(AuthUser).filter_by(login_id="Admin@001").one()
        assert user.status == "SUSPENDED"
        assert verify_password("OriginalPass#123", user.password_hash)
        assert not verify_password("DifferentPass#456", user.password_hash)
        assert user.must_change_password is False


def test_emergency_recovery_ignores_other_configured_account_passwords():
    _create_user(
        "Admin@001",
        "OriginalPass#123",
        role="SUPER_ADMIN",
        status="SUSPENDED",
    )
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "RecoveredPass#456"
    os.environ["BOOTSTRAP_MANAGER_PASSWORD"] = "ManagerPass#123"
    os.environ["BOOTSTRAP_FORCE_RESET"] = "true"
    os.environ["BOOTSTRAP_RECOVERY_LOGIN_ID"] = "Admin@001"
    bootstrap_users()

    with SessionLocal() as db:
        assert db.query(AuthUser).filter_by(login_id="Manager@001").one_or_none() is None


def test_explicit_super_admin_recovery_resets_only_target_and_revokes_sessions():
    _create_user(
        "Admin@001",
        "OriginalPass#123",
        role="SUPER_ADMIN",
        status="SUSPENDED",
        must_change_password=False,
    )
    _create_user("Manager@001", "ManagerPass#123", role="MANAGER", status="SUSPENDED")
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "RecoveredPass#456"
    os.environ["BOOTSTRAP_FORCE_RESET"] = "true"
    os.environ["BOOTSTRAP_RECOVERY_LOGIN_ID"] = "Admin@001"
    bootstrap_users()

    with SessionLocal() as db:
        admin = db.query(AuthUser).filter_by(login_id="Admin@001").one()
        manager = db.query(AuthUser).filter_by(login_id="Manager@001").one()
        assert admin.status == "ACTIVE"
        assert admin.must_change_password is True
        assert admin.token_version == 1
        assert verify_password("RecoveredPass#456", admin.password_hash)
        assert manager.status == "SUSPENDED"
        assert verify_password("ManagerPass#123", manager.password_hash)


def test_production_configuration_rejects_sqlite_insecure_secret_and_wildcard_cors():
    common = {
        "app_env": "production",
        "database_url": "postgresql://user:pass@db.example.com/app",
        "jwt_secret": "production-secret-that-is-long-enough-2026",
        "cors_origins": "https://office.example.com",
    }
    valid = Settings(_env_file=None, **common)
    assert valid.normalized_database_url.startswith("postgresql+psycopg://")

    with __import__("pytest").raises(ValidationError):
        Settings(_env_file=None, **{**common, "database_url": "sqlite:///./prod.db"})
    with __import__("pytest").raises(ValidationError):
        Settings(
            _env_file=None,
            **{**common, "jwt_secret": "development-only-change-me-please-32chars"},
        )
    with __import__("pytest").raises(ValidationError):
        Settings(_env_file=None, **{**common, "cors_origins": "*"})


def test_cors_allows_only_configured_origins():
    allowed = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://fames-r-office-pro-frontend.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://fames-r-office-pro-frontend.vercel.app"

    denied = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_alembic_revision_is_current():
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "20260719_01"


def test_batch2_and_batch3_routes_are_not_mixed_into_batch1():
    paths = set(client.get("/openapi.json").json()["paths"])
    assert not any(path.startswith("/api/v1/clients") for path in paths)
    assert not any(path.startswith("/api/v1/jobs") for path in paths)


def test_postgresql_driver_and_production_url_normalization_are_available():
    import psycopg
    from sqlalchemy.engine import make_url

    settings = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql://user:pass@db.example.com/fames",
        jwt_secret="production-secret-that-is-long-enough-2026",
        cors_origins="https://office.example.com",
    )
    url = make_url(settings.normalized_database_url)
    assert psycopg.__version__
    assert url.drivername == "postgresql+psycopg"
