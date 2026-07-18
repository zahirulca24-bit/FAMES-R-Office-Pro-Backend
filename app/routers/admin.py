from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_super_admin
from app.models import AuthAuditLog, AuthUser
from app.schemas import AdminCreateUserRequest, AdminStatusRequest, UserView
from app.security import hash_password


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
ALLOWED_STATUSES = {"ACTIVE", "PENDING_ACTIVATION", "SUSPENDED", "DISABLED"}


@router.post("/users", response_model=UserView, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    admin: AuthUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserView:
    login_id = payload.login_id.strip()
    email = payload.email.lower() if payload.email else None
    duplicate_filters = [func.lower(AuthUser.login_id) == login_id.lower()]
    if email:
        duplicate_filters.append(func.lower(AuthUser.email) == email)
    existing = db.scalar(select(AuthUser).where(or_(*duplicate_filters)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ID or email already exists")

    user = AuthUser(
        login_id=login_id,
        email=email,
        full_name=payload.full_name.strip(),
        role=payload.role,
        password_hash=hash_password(payload.password),
        status="ACTIVE",
        must_change_password=payload.must_change_password,
    )
    db.add(user)
    db.flush()
    db.add(
        AuthAuditLog(
            user_id=admin.id,
            login_id=admin.login_id,
            event_type="USER_CREATED",
            detail=f"created={user.login_id}",
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ID or email already exists") from exc
    db.refresh(user)
    return UserView.model_validate(user)


@router.patch("/users/{login_id}/status", response_model=UserView)
def set_user_status(
    login_id: str,
    payload: AdminStatusRequest,
    admin: AuthUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserView:
    new_status = payload.status.strip().upper()
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid account status")

    user = db.scalar(select(AuthUser).where(func.lower(AuthUser.login_id) == login_id.strip().lower()))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and new_status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own Super Admin account")

    if user.status != new_status:
        user.status = new_status
        user.token_version += 1
    db.add(
        AuthAuditLog(
            user_id=admin.id,
            login_id=admin.login_id,
            event_type="USER_STATUS_CHANGED",
            detail=f"target={user.login_id};status={new_status}",
        )
    )
    db.commit()
    db.refresh(user)
    return UserView.model_validate(user)
