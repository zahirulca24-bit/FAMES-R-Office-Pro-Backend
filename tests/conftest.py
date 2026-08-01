import os
from pathlib import Path

import pytest


TEST_DATABASE_PATH = (Path.cwd() / ".pytest_fames_backend.db").resolve()
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret-that-is-definitely-long-enough-12345"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import AuthUser  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Provide one disposable database for the complete test session."""
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.add(
            AuthUser(
                login_id="Admin@001",
                email="admin@example.com",
                full_name="Admin",
                role="SUPER_ADMIN",
                password_hash=hash_password("StrongPass#123"),
                status="ACTIVE",
                must_change_password=True,
            )
        )
        db.commit()

    yield

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
