"""Add notifications, backup verification and production readiness checks.

Revision ID: 20260808_0019
Revises: 20260808_0018
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0019"
down_revision = "20260808_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_key", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("recipient_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject", sa.String(250), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    for name, cols in [
        ("ix_notification_events_event_key", ["event_key"]),
        ("ix_notification_events_resource_type", ["resource_type"]),
        ("ix_notification_events_resource_id", ["resource_id"]),
        ("ix_notification_events_recipient_user_id", ["recipient_user_id"]),
        ("ix_notification_events_status", ["status"]),
        ("ix_notification_events_channel", ["channel"]),
        ("ix_notification_events_created_at", ["created_at"]),
    ]:
        op.create_index(name, "notification_events", cols)

    op.create_table(
        "backup_verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("backup_reference", sa.String(200), nullable=False, unique=True),
        sa.Column("backup_status", sa.String(30), nullable=False),
        sa.Column("restore_test_status", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verified_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_backup_verifications_backup_status", "backup_verifications", ["backup_status"])
    op.create_index("ix_backup_verifications_restore_test_status", "backup_verifications", ["restore_test_status"])
    op.create_index("ix_backup_verifications_verified_at", "backup_verifications", ["verified_at"])

    op.create_table(
        "production_readiness_checks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("check_key", sa.String(100), nullable=False, unique=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("checked_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_production_readiness_checks_passed", "production_readiness_checks", ["passed"])
    op.create_index("ix_production_readiness_checks_checked_at", "production_readiness_checks", ["checked_at"])


def downgrade() -> None:
    op.drop_table("production_readiness_checks")
    op.drop_table("backup_verifications")
    op.drop_table("notification_events")
