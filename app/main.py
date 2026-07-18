from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.health import check_readiness
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router


logger = logging.getLogger(__name__)
_startup_bootstrap_error: str | None = None


def _run_startup_bootstrap() -> None:
    """Create missing users or run an explicitly targeted Super Admin recovery.

    Bootstrap failures are logged and surfaced through readiness rather than taking
    the process-liveness endpoint offline.
    """
    global _startup_bootstrap_error
    _startup_bootstrap_error = None
    has_password = any(
        key.startswith("BOOTSTRAP_") and key.endswith("_PASSWORD") and value
        for key, value in os.environ.items()
    )
    force_recovery = os.getenv("BOOTSTRAP_FORCE_RESET", "").strip().lower() in {"1", "true", "yes", "on"}
    if not has_password and not force_recovery:
        return

    try:
        from scripts.bootstrap_users import main as bootstrap_users

        bootstrap_users()
    except Exception as exc:
        _startup_bootstrap_error = f"bootstrap error: {type(exc).__name__}"
        logger.exception("Startup bootstrap failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    _run_startup_bootstrap()
    yield


settings = get_settings()
app = FastAPI(title="FAMES & R Office PRO API", version="0.1.1", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/health")
def legacy_health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/api/v1/health")
def legacy_api_health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/api/v1/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/api/v1/health/ready")
def health_ready() -> dict[str, object]:
    result = check_readiness(startup_error=_startup_bootstrap_error)
    if not result.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": result.checks},
        )
    return {"status": "ready", "checks": result.checks}
