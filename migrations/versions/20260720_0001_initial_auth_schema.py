"""Initial authentication schema.

Revision ID: 20260720_0001
Revises:
Create Date: 2026-07-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260720_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
    op.create_index(op.f("ix_auth_users_email"), "auth_users", ["email"], unique=True)
    op.create_index(op.f("ix_auth_users_login_id"), "auth_users", ["login_id"], unique=True)
    op.create_index(op.f("ix_auth_users_role"), "auth_users", ["role"], unique=False)
    op.create_index(op.f("ix_auth_users_status"), "auth_users", ["status"], unique=False)

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
    op.create_index(op.f("ix_auth_audit_logs_created_at"), "auth_audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_auth_audit_logs_event_type"), "auth_audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_auth_audit_logs_login_id"), "auth_audit_logs", ["login_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_audit_logs_login_id"), table_name="auth_audit_logs")
    op.drop_index(op.f("ix_auth_audit_logs_event_type"), table_name="auth_audit_logs")
    op.drop_index(op.f("ix_auth_audit_logs_created_at"), table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")
    op.drop_index(op.f("ix_auth_users_status"), table_name="auth_users")
    op.drop_index(op.f("ix_auth_users_role"), table_name="auth_users")
    op.drop_index(op.f("ix_auth_users_login_id"), table_name="auth_users")
    op.drop_index(op.f("ix_auth_users_email"), table_name="auth_users")
    op.drop_table("auth_users")
