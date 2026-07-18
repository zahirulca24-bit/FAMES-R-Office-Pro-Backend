import logging
import os
from dataclasses import dataclass

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AuthUser
from app.security import hash_password


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootstrapUser:
    login_id: str
    email: str | None
    full_name: str
    role: str
    password_env: str
    status: str


USERS = [
    BootstrapUser("Admin@001", "zahirul.ca24@gmail.com", "FAMES & R Super Admin", "SUPER_ADMIN", "BOOTSTRAP_ADMIN_PASSWORD", "ACTIVE"),
    BootstrapUser("Manager@001", "manager.fames@gmail.com", "FAMES & R Manager", "MANAGER", "BOOTSTRAP_MANAGER_PASSWORD", "ACTIVE"),
    BootstrapUser("AssistantDev@001", "Nayan.macrom@gmail.com", "Nayan", "ASSISTANT_DEVELOPER", "BOOTSTRAP_ASSISTANT_DEVELOPER_PASSWORD", "ACTIVE"),
    BootstrapUser("Student@001", "bayazidmridha6@gmail.com", "Bayazid", "STUDENT", "BOOTSTRAP_STUDENT_001_PASSWORD", "ACTIVE"),
    BootstrapUser("Student@002", "iftekhairul2000@gmail.com", "Iftekhar", "STUDENT", "BOOTSTRAP_STUDENT_002_PASSWORD", "ACTIVE"),
    BootstrapUser("Student@003", "tanjumaktertisha665@gmail.com", "Tanjum", "STUDENT", "BOOTSTRAP_STUDENT_003_PASSWORD", "ACTIVE"),
    BootstrapUser("Student@004", "hemadryroy44@gmail.com", "Hemadry", "STUDENT", "BOOTSTRAP_STUDENT_004_PASSWORD", "ACTIVE"),
    BootstrapUser("Shafi@001", os.getenv("BOOTSTRAP_PARTNER_EMAIL") or None, "Mr. Shafi Uddin Ahmed, FCA", "PARTNER", "BOOTSTRAP_PARTNER_PASSWORD", "PENDING_ACTIVATION"),
]


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    """Create missing bootstrap users and support one explicit Super Admin recovery.

    Existing accounts are never reactivated, reassigned, or password-reset during a
    normal restart. Emergency recovery requires BOOTSTRAP_FORCE_RESET=true and
    BOOTSTRAP_RECOVERY_LOGIN_ID naming one configured SUPER_ADMIN account.
    """
    force_reset = _env_flag("BOOTSTRAP_FORCE_RESET")
    recovery_login_id = os.getenv("BOOTSTRAP_RECOVERY_LOGIN_ID", "").strip()
    if force_reset and not recovery_login_id:
        raise RuntimeError("BOOTSTRAP_RECOVERY_LOGIN_ID is required when BOOTSTRAP_FORCE_RESET=true")

    configured_recovery = next(
        (item for item in USERS if item.login_id.lower() == recovery_login_id.lower()),
        None,
    )
    if force_reset and (configured_recovery is None or configured_recovery.role != "SUPER_ADMIN"):
        raise RuntimeError("Emergency recovery is restricted to a configured SUPER_ADMIN account")

    errors: list[str] = []
    with SessionLocal() as db:
        for item in USERS:
            is_recovery_target = force_reset and item.login_id.lower() == recovery_login_id.lower()
            if force_reset and not is_recovery_target:
                continue

            password = os.getenv(item.password_env)
            if not password:
                if is_recovery_target:
                    errors.append(f"{item.password_env} is required for recovery")
                continue
            if len(password) < 10:
                errors.append(f"{item.password_env} must be at least 10 characters")
                continue

            try:
                user = db.scalar(select(AuthUser).where(func.lower(AuthUser.login_id) == item.login_id.lower()))
                if user is None:
                    user = AuthUser(
                        login_id=item.login_id,
                        email=item.email,
                        full_name=item.full_name,
                        role=item.role,
                        password_hash=hash_password(password),
                        status=item.status,
                        must_change_password=True,
                    )
                    db.add(user)
                    logger.info("Created bootstrap user %s", item.login_id)
                elif is_recovery_target:
                    user.password_hash = hash_password(password)
                    user.failed_login_count = 0
                    user.locked_until = None
                    user.status = "ACTIVE"
                    user.must_change_password = True
                    user.token_version += 1
                    logger.warning("Recovered Super Admin %s; existing sessions revoked", item.login_id)
                else:
                    logger.info("Preserved existing account %s without mutation", item.login_id)
                db.commit()
            except Exception as exc:
                db.rollback()
                errors.append(f"{item.login_id}: {type(exc).__name__}: {exc}")

    if errors:
        raise RuntimeError("; ".join(errors))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
