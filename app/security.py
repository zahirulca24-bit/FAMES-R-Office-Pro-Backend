from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def create_access_token(
    *,
    subject: str,
    login_id: str,
    role: str,
    token_version: int,
    remember_me: bool,
) -> tuple[str, int]:
    settings = get_settings()
    minutes = settings.remember_token_minutes if remember_me else settings.access_token_minutes
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "login_id": login_id,
        "role": role,
        "ver": token_version,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload
