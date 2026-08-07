from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import Base, engine
from app.foundation.http import ApiError, CorrelationIdMiddleware, correlation_id_from_request, error_response
from app.routers.admin import router as admin_router
from app.routers.audit_execution import router as audit_execution_router
from app.routers.audit_planning import router as audit_planning_router
from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.documents import router as documents_router
from app.routers.engagement_closure import router as engagement_closure_router
from app.routers.engagements import router as engagements_router
from app.routers.engagement_tasks import router as engagement_tasks_router
from app.routers.engagement_templates import router as engagement_templates_router
from app.routers.manager import router as manager_router
from app.routers.staff import router as staff_router
from app.routers.workforce import router as workforce_router
from app.routers.working_papers import router as working_papers_router
import app.audit_execution_models  # noqa: F401
import app.audit_models  # noqa: F401
import app.client_lifecycle_models  # noqa: F401
import app.client_models  # noqa: F401
import app.document_models  # noqa: F401
import app.engagement_closure_models  # noqa: F401
import app.engagement_models  # noqa: F401
import app.engagement_template_models  # noqa: F401
import app.staff_models  # noqa: F401
import app.workforce_models  # noqa: F401
import app.working_paper_models  # noqa: F401
import app.workflow_models  # noqa: F401


def _run_startup_bootstrap() -> None:
    if not any(key.startswith("BOOTSTRAP_") and key.endswith("_PASSWORD") and value for key, value in os.environ.items()):
        return
    try:
        from scripts.bootstrap_users import main as bootstrap_users
        bootstrap_users()
    except Exception as exc:
        print(f"STARTUP BOOTSTRAP ERROR: {type(exc).__name__}: {exc}")


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env.lower() in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    _run_startup_bootstrap()
    yield


app = FastAPI(title="FAMES & R Office PRO API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError):
    return error_response(exc, correlation_id_from_request(request))


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(manager_router)
app.include_router(clients_router)
app.include_router(staff_router)
app.include_router(workforce_router)
app.include_router(engagements_router)
app.include_router(engagement_templates_router)
app.include_router(engagement_tasks_router)
app.include_router(engagement_closure_router)
app.include_router(documents_router)
app.include_router(working_papers_router)
app.include_router(audit_planning_router)
app.include_router(audit_execution_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/api/v1/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "fames-r-office-pro-backend"}


@app.get("/health/ready")
def health_ready(response: Response) -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "service": "fames-r-office-pro-backend", "database": "unavailable"}
    return {"status": "ok", "service": "fames-r-office-pro-backend", "database": "ready"}
