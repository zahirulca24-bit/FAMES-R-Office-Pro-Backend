"""Batch 1 auth baseline and token revocation support.

Revision ID: 20260719_01
Revises: None
Create Date: 2026-07-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {item["name"] for item in inspector.get_indexes(table_name) if item.get("name")}


def _create_auth_users() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("login_id", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("login_id"),
    )


def _create_auth_user_indexes(existing: set[str] | None = None) -> None:
    existing = existing or set()
    for name, columns in {
        "ix_auth_users_login_id": ["login_id"],
        "ix_auth_users_email": ["email"],
        "ix_auth_users_role": ["role"],
        "ix_auth_users_status": ["status"],
    }.items():
        if name not in existing:
            op.create_index(name, "auth_users", columns, unique=False)


def _create_auth_audit_logs() -> None:
    op.create_table(
        "auth_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("login_id", sa.String(length=80), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_auth_audit_indexes(existing: set[str] | None = None) -> None:
    existing = existing or set()
    for name, columns in {
        "ix_auth_audit_logs_login_id": ["login_id"],
        "ix_auth_audit_logs_event_type": ["event_type"],
        "ix_auth_audit_logs_created_at": ["created_at"],
    }.items():
        if name not in existing:
            op.create_index(name, "auth_audit_logs", columns, unique=False)


def upgrade() -> None:
    # Offline SQL cannot inspect a target database. Generate the complete fresh
    # schema; online upgrades retain the adoption path for pre-Alembic databases.
    if op.get_context().as_sql:
        _create_auth_users()
        _create_auth_user_indexes()
        _create_auth_audit_logs()
        _create_auth_audit_indexes()
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "auth_users" not in tables:
        _create_auth_users()
    else:
        columns = {column["name"] for column in inspector.get_columns("auth_users")}
        if "token_version" not in columns:
            op.add_column(
                "auth_users",
                sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
            )

    inspector = sa.inspect(bind)
    _create_auth_user_indexes(_index_names(inspector, "auth_users"))

    tables = set(sa.inspect(bind).get_table_names())
    if "auth_audit_logs" not in tables:
        _create_auth_audit_logs()

    inspector = sa.inspect(bind)
    _create_auth_audit_indexes(_index_names(inspector, "auth_audit_logs"))


def downgrade() -> None:
    raise RuntimeError(
        "Revision 20260719_01 is an adoption baseline and cannot be safely downgraded "
        "because the auth tables may predate Alembic."
    )
