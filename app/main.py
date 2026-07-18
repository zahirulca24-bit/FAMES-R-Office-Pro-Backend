from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router


def _run_startup_bootstrap() -> None:
    """Create/update bootstrap users only when a bootstrap password is explicitly set.

    This keeps free-tier Render deployments shell-free. Remove the bootstrap
    environment variable after the first successful deployment so passwords
    are not reset on later restarts.
    """
    if not any(
        key.startswith("BOOTSTRAP_") and key.endswith("_PASSWORD") and value
        for key, value in os.environ.items()
    ):
        return

    from scripts.bootstrap_users import main as bootstrap_users

    bootstrap_users()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_startup_bootstrap()
    yield


settings = get_settings()
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/api/v1/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}
