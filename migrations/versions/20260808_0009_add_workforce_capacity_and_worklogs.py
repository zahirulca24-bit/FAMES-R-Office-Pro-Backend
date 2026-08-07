"""Add attendance, leave, capacity assignments and worklogs.

Revision ID: 20260808_0009
Revises: 20260808_0008
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0009"
down_revision = "20260808_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("worked_minutes", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("staff_id", "work_date", name="uq_attendance_staff_date"),
    )
    op.create_index("ix_attendance_records_staff_id", "attendance_records", ["staff_id"])
    op.create_index("ix_attendance_records_work_date", "attendance_records", ["work_date"])
    op.create_index("ix_attendance_records_status", "attendance_records", ["status"])

    op.create_table(
        "leave_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_date", sa.Date(), nullable=False),
        sa.Column("leave_type", sa.String(40), nullable=False),
        sa.Column("leave_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approved_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("staff_id", "leave_date", "leave_type", name="uq_leave_staff_date_type"),
    )
    op.create_index("ix_leave_records_staff_id", "leave_records", ["staff_id"])
    op.create_index("ix_leave_records_leave_date", "leave_records", ["leave_date"])
    op.create_index("ix_leave_records_status", "leave_records", ["status"])

    op.create_table(
        "capacity_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("assigned_minutes", sa.Integer(), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("staff_id", "work_date", "source_type", "source_id", name="uq_capacity_assignment_source"),
    )
    op.create_index("ix_capacity_assignments_staff_id", "capacity_assignments", ["staff_id"])
    op.create_index("ix_capacity_assignments_work_date", "capacity_assignments", ["work_date"])

    op.create_table(
        "staff_worklogs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_staff_worklogs_staff_id", "staff_worklogs", ["staff_id"])
    op.create_index("ix_staff_worklogs_work_date", "staff_worklogs", ["work_date"])
    op.create_index("ix_staff_worklogs_resource_type", "staff_worklogs", ["resource_type"])
    op.create_index("ix_staff_worklogs_resource_id", "staff_worklogs", ["resource_id"])
    op.create_index("ix_staff_worklogs_status", "staff_worklogs", ["status"])


def downgrade() -> None:
    op.drop_table("staff_worklogs")
    op.drop_table("capacity_assignments")
    op.drop_table("leave_records")
    op.drop_table("attendance_records")
