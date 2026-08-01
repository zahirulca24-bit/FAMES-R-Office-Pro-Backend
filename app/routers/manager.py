from fastapi import APIRouter, Depends

from app.deps import require_manager
from app.models import AuthUser


router = APIRouter(prefix="/api/v1/manager", tags=["manager"])


@router.get("/access-check")
def manager_access_check(user: AuthUser = Depends(require_manager)) -> dict[str, object]:
    return {
        "status": "ok",
        "login_id": user.login_id,
        "role": user.role,
        "capabilities": [
            "client_operations",
            "staff_assignment",
            "job_management",
            "audit_workflow",
            "compliance_management",
        ],
    }
