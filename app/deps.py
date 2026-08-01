from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuthUser
from app.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)
MANAGER_ACCESS_ROLES = {"SUPER_ADMIN", "PARTNER", "MANAGER"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user = db.get(AuthUser, str(payload.get("sub", "")))
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is not active")

    token_version = payload.get("ver")
    if not isinstance(token_version, int) or token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid")
    return user


def require_password_changed(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.must_change_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password change required")
    return user


def require_super_admin(user: AuthUser = Depends(require_password_changed)) -> AuthUser:
    if user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access required")
    return user


def require_manager(user: AuthUser = Depends(require_password_changed)) -> AuthUser:
    if user.role not in MANAGER_ACCESS_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required")
    return user
