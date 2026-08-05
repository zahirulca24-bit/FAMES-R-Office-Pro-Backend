from __future__ import annotations

import getpass
import os
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal
from app.models import AuthUser
from app.security import hash_password


@dataclass(frozen=True)
class BootstrapInput:
    login_id: str
    full_name: str
    email: str | None
    password: str


def _required_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def read_bootstrap_input() -> BootstrapInput:
    login_id = _required_env("BOOTSTRAP_LOGIN_ID", "Admin@001")
    full_name = _required_env("BOOTSTRAP_FULL_NAME", "FAMES & R Super Admin")
    email_value = os.getenv("BOOTSTRAP_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_PASSWORD")
    if password is None:
        password = getpass.getpass("Temporary password: ")
    confirmation = os.getenv("BOOTSTRAP_PASSWORD_CONFIRM")
    if confirmation is None:
        confirmation = getpass.getpass("Confirm temporary password: ")
    if password != confirmation:
        raise ValueError("Password confirmation does not match")
    return BootstrapInput(
        login_id=login_id,
        full_name=full_name,
        email=email_value or None,
        password=password,
    )


def bootstrap_super_admin(data: BootstrapInput) -> str:
    password_hash = hash_password(data.password)
    with SessionLocal() as db:
        try:
            existing = db.scalar(select(AuthUser).where(AuthUser.login_id == data.login_id))
            if existing is not None:
                if existing.role != "SUPER_ADMIN":
                    raise ValueError("Login ID already belongs to a non-SUPER_ADMIN account")
                existing.full_name = data.full_name
                existing.email = data.email
                existing.password_hash = password_hash
                existing.status = "ACTIVE"
                existing.must_change_password = True
                existing.failed_login_count = 0
                existing.locked_until = None
                existing.token_version += 1
                action = "updated"
            else:
                db.add(
                    AuthUser(
                        login_id=data.login_id,
                        email=data.email,
                        full_name=data.full_name,
                        role="SUPER_ADMIN",
                        password_hash=password_hash,
                        status="ACTIVE",
                        must_change_password=True,
                    )
                )
                action = "created"
            db.commit()
            return action
        except Exception:
            db.rollback()
            raise


def main() -> int:
    try:
        data = read_bootstrap_input()
        action = bootstrap_super_admin(data)
    except (ValueError, SQLAlchemyError) as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1
    print(f"SUPER_ADMIN {action}: {data.login_id}")
    print("Temporary password was not logged. Password change is required at first login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
