from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.db import engine


EXPECTED_ALEMBIC_REVISION = "20260719_01"
REQUIRED_TABLES = {"auth_users", "auth_audit_logs", "alembic_version"}
REQUIRED_AUTH_USER_COLUMNS = {
    "id",
    "login_id",
    "email",
    "full_name",
    "role",
    "password_hash",
    "status",
    "must_change_password",
    "token_version",
    "failed_login_count",
    "locked_until",
    "last_login_at",
    "password_changed_at",
    "created_at",
    "updated_at",
}


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str]


def check_readiness(*, startup_error: str | None = None) -> ReadinessResult:
    checks: dict[str, str] = {}
    if startup_error:
        checks["startup"] = startup_error
        return ReadinessResult(False, checks)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            checks["database"] = "ok"

            table_names = set(inspect(connection).get_table_names())
            missing = sorted(REQUIRED_TABLES - table_names)
            if missing:
                checks["schema"] = f"missing tables: {', '.join(missing)}"
                return ReadinessResult(False, checks)
            auth_user_columns = {column["name"] for column in inspect(connection).get_columns("auth_users")}
            missing_columns = sorted(REQUIRED_AUTH_USER_COLUMNS - auth_user_columns)
            if missing_columns:
                checks["schema"] = f"auth_users missing columns: {', '.join(missing_columns)}"
                return ReadinessResult(False, checks)
            checks["schema"] = "ok"

            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if revision != EXPECTED_ALEMBIC_REVISION:
                checks["migration"] = f"expected {EXPECTED_ALEMBIC_REVISION}, found {revision or 'none'}"
                return ReadinessResult(False, checks)
            checks["migration"] = "ok"
    except SQLAlchemyError as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        return ReadinessResult(False, checks)

    return ReadinessResult(True, checks)
