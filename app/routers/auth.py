from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import AuthAuditLog, AuthUser
from app.schemas import ChangePasswordRequest, LoginRequest, LoginResponse, UserView
from app.security import create_access_token, hash_password, password_needs_rehash, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _audit(
    db: Session,
    request: Request,
    event_type: str,
    user: AuthUser | None = None,
    login_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AuthAuditLog(
            user_id=user.id if user else None,
            login_id=user.login_id if user else login_id,
            event_type=event_type,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            detail=detail,
        )
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    settings = get_settings()
    normalized = payload.login_id.strip().lower()
    user = db.scalar(select(AuthUser).where(func.lower(AuthUser.login_id) == normalized))

    if user is None:
        _audit(db, request, "LOGIN_FAILED", login_id=payload.login_id.strip(), detail="unknown_login_id")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login ID or password")

    now = datetime.now(timezone.utc)
    if user.status != "ACTIVE":
        _audit(db, request, "LOGIN_BLOCKED", user=user, detail=f"status={user.status}")
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    if user.locked_until and user.locked_until > now:
        _audit(db, request, "LOGIN_BLOCKED", user=user, detail="temporary_lock")
        db.commit()
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked. Try again later.")

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_failures:
            user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
            user.failed_login_count = 0
        _audit(db, request, "LOGIN_FAILED", user=user, detail="invalid_password")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login ID or password")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    token, expires_in = create_access_token(
        subject=user.id,
        login_id=user.login_id,
        role=user.role,
        token_version=user.token_version,
        remember_me=payload.remember_me,
    )
    _audit(db, request, "LOGIN_SUCCESS", user=user)
    db.commit()
    db.refresh(user)

    return LoginResponse(access_token=token, expires_in=expires_in, user=UserView.model_validate(user))


@router.get("/me", response_model=UserView)
def me(user: AuthUser = Depends(get_current_user)) -> UserView:
    return UserView.model_validate(user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not verify_password(payload.current_password, user.password_hash):
        _audit(db, request, "PASSWORD_CHANGE_FAILED", user=user, detail="invalid_current_password")
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    user.token_version += 1
    _audit(db, request, "PASSWORD_CHANGED", user=user, detail="all_previous_tokens_revoked")
    db.commit()
    return {"message": "Password changed successfully. Please sign in again."}
