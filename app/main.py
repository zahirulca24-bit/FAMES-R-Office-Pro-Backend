from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import Base, engine
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.manager import router as manager_router


def _run_startup_bootstrap() -> None:
    """Create/update bootstrap users only when a bootstrap password is explicitly set.

    Bootstrap failures must never take the API offline. Remove bootstrap password
    environment variables after the intended account has been created successfully.
    """
    if not any(
        key.startswith("BOOTSTRAP_") and key.endswith("_PASSWORD") and value
        for key, value in os.environ.items()
    ):
        return

    try:
        from scripts.bootstrap_users import main as bootstrap_users

        bootstrap_users()
    except Exception as exc:
        print(f"STARTUP BOOTSTRAP ERROR: {type(exc).__name__}: {exc}")


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Disposable development/test databases may create their schema automatically.
    # Every hosted environment must receive schema changes through Alembic.
    if settings.app_env.lower() in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    _run_startup_bootstrap()
    yield


app = FastAPI(title="FAMES & R Office PRO API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(manager_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/api/v1/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/health/live")
def health_live() -> dict[str, str]:
    """Process-level liveness check; does not depend on external services."""
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/health/ready")
def health_ready(response: Response) -> dict[str, str]:
    """Readiness check that proves the configured database accepts a query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "service": "fames-r-office-pro-backend",
            "database": "unavailable",
        }

    return {
        "status": "ok",
        "service": "fames-r-office-pro-backend",
        "database": "ready",
    }
