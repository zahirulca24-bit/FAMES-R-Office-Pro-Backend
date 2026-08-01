import os

from sqlalchemy import func, select

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import AuthUser
from app.security import hash_password


USERS = [
    ("Admin@001", "zahirul.ca24@gmail.com", "FAMES & R Super Admin", "SUPER_ADMIN", "BOOTSTRAP_ADMIN_PASSWORD", "ACTIVE"),
    ("Manager@001", "manager.fames@gmail.com", "FAMES & R Manager 1", "MANAGER", "BOOTSTRAP_MANAGER_PASSWORD", "ACTIVE"),
    (
        "Manager@002",
        os.getenv("BOOTSTRAP_MANAGER_002_EMAIL") or None,
        os.getenv("BOOTSTRAP_MANAGER_002_NAME") or "FAMES & R Manager 2",
        "MANAGER",
        "BOOTSTRAP_MANAGER_002_PASSWORD",
        "ACTIVE",
    ),
    ("AssistantDev@001", "Nayan.macrom@gmail.com", "Nayan", "ASSISTANT_DEVELOPER", "BOOTSTRAP_ASSISTANT_DEVELOPER_PASSWORD", "ACTIVE"),
    ("Student@001", "bayazidmridha6@gmail.com", "Bayazid", "STUDENT", "BOOTSTRAP_STUDENT_001_PASSWORD", "ACTIVE"),
    ("Student@002", "iftekhairul2000@gmail.com", "Iftekhar", "STUDENT", "BOOTSTRAP_STUDENT_002_PASSWORD", "ACTIVE"),
    ("Student@003", "tanjumaktertisha665@gmail.com", "Tanjum", "STUDENT", "BOOTSTRAP_STUDENT_003_PASSWORD", "ACTIVE"),
    ("Student@004", "hemadryroy44@gmail.com", "Hemadry", "STUDENT", "BOOTSTRAP_STUDENT_004_PASSWORD", "ACTIVE"),
    ("Shafi@001", os.getenv("BOOTSTRAP_PARTNER_EMAIL") or None, "Mr. Shafi Uddin Ahmed, FCA", "PARTNER", "BOOTSTRAP_PARTNER_PASSWORD", "PENDING_ACTIVATION"),
]


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    """Create missing bootstrap users without resetting existing passwords.

    Set BOOTSTRAP_FORCE_RESET=true only for an intentional no-shell recovery.
    After recovery succeeds, remove/disable BOOTSTRAP_FORCE_RESET again.
    """
    settings = get_settings()
    if settings.app_env.lower() in {"development", "test"}:
        Base.metadata.create_all(bind=engine)

    force_reset = _env_flag("BOOTSTRAP_FORCE_RESET")

    with SessionLocal() as db:
        for login_id, email, full_name, role, password_env, status in USERS:
            password = os.getenv(password_env)
            if not password:
                print(f"SKIP {login_id}: {password_env} is not set")
                continue
            if len(password) < 10:
                print(f"SKIP {login_id}: {password_env} must be at least 10 characters")
                continue

            try:
                user = db.scalar(select(AuthUser).where(func.lower(AuthUser.login_id) == login_id.lower()))

                if user is None:
                    user = AuthUser(
                        login_id=login_id,
                        email=email,
                        full_name=full_name,
                        role=role,
                        password_hash=hash_password(password),
                        status=status,
                        must_change_password=True,
                    )
                    db.add(user)
                    print(f"CREATE {login_id}")
                else:
                    # Keep identity metadata synchronized, but never rotate a working
                    # password merely because the service restarted or redeployed.
                    user.email = email
                    user.full_name = full_name
                    user.role = role
                    user.status = status

                    if force_reset:
                        user.password_hash = hash_password(password)
                        user.failed_login_count = 0
                        user.locked_until = None
                        user.must_change_password = True
                        user.token_version += 1
                        print(f"RECOVER {login_id}")
                    else:
                        print(f"KEEP {login_id}: existing password preserved")

                db.commit()
            except Exception as exc:
                db.rollback()
                print(f"BOOTSTRAP ERROR {login_id}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
