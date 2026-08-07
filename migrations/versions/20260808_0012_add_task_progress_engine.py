"""Add task dependency, deadline and weighted progress engine.

Revision ID: 20260808_0012
Revises: 20260808_0011
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0012"
down_revision = "20260808_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("engagement_generated_tasks", sa.Column("parent_task_id", sa.String(36), nullable=True))
    op.add_column("engagement_generated_tasks", sa.Column("assignee_staff_id", sa.String(36), nullable=True))
    op.add_column("engagement_generated_tasks", sa.Column("reviewer_staff_id", sa.String(36), nullable=True))
    op.add_column("engagement_generated_tasks", sa.Column("weight_points", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("engagement_generated_tasks", sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("engagement_generated_tasks", sa.Column("escalation_state", sa.String(30), nullable=False, server_default="NONE"))
    op.add_column("engagement_generated_tasks", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("engagement_generated_tasks", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("engagement_generated_tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("engagement_generated_tasks", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("engagement_generated_tasks", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

    op.create_foreign_key("fk_generated_task_parent", "engagement_generated_tasks", "engagement_generated_tasks", ["parent_task_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_generated_task_assignee", "engagement_generated_tasks", "staff_profiles", ["assignee_staff_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_generated_task_reviewer", "engagement_generated_tasks", "staff_profiles", ["reviewer_staff_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_generated_task_parent", "engagement_generated_tasks", ["parent_task_id"])
    op.create_index("ix_generated_task_assignee", "engagement_generated_tasks", ["assignee_staff_id"])
    op.create_index("ix_generated_task_reviewer", "engagement_generated_tasks", ["reviewer_staff_id"])
    op.create_index("ix_generated_task_escalation", "engagement_generated_tasks", ["escalation_state"])

    op.create_table(
        "engagement_task_dependencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("engagement_generated_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("depends_on_task_id", sa.String(36), sa.ForeignKey("engagement_generated_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dependency_type", sa.String(30), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_engagement_task_dependency"),
    )
    op.create_index("ix_engagement_task_dependencies_engagement_id", "engagement_task_dependencies", ["engagement_id"])
    op.create_index("ix_engagement_task_dependencies_task_id", "engagement_task_dependencies", ["task_id"])
    op.create_index("ix_engagement_task_dependencies_depends_on_task_id", "engagement_task_dependencies", ["depends_on_task_id"])

    op.create_table(
        "engagement_task_status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("engagement_generated_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=False),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_engagement_task_status_history_task_id", "engagement_task_status_history", ["task_id"])
    op.create_index("ix_engagement_task_status_history_created_at", "engagement_task_status_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("engagement_task_status_history")
    op.drop_table("engagement_task_dependencies")

    op.drop_index("ix_generated_task_escalation", table_name="engagement_generated_tasks")
    op.drop_index("ix_generated_task_reviewer", table_name="engagement_generated_tasks")
    op.drop_index("ix_generated_task_assignee", table_name="engagement_generated_tasks")
    op.drop_index("ix_generated_task_parent", table_name="engagement_generated_tasks")
    op.drop_constraint("fk_generated_task_reviewer", "engagement_generated_tasks", type_="foreignkey")
    op.drop_constraint("fk_generated_task_assignee", "engagement_generated_tasks", type_="foreignkey")
    op.drop_constraint("fk_generated_task_parent", "engagement_generated_tasks", type_="foreignkey")

    op.drop_column("engagement_generated_tasks", "updated_at")
    op.drop_column("engagement_generated_tasks", "escalated_at")
    op.drop_column("engagement_generated_tasks", "completed_at")
    op.drop_column("engagement_generated_tasks", "started_at")
    op.drop_column("engagement_generated_tasks", "version")
    op.drop_column("engagement_generated_tasks", "escalation_state")
    op.drop_column("engagement_generated_tasks", "progress_percent")
    op.drop_column("engagement_generated_tasks", "weight_points")
    op.drop_column("engagement_generated_tasks", "reviewer_staff_id")
    op.drop_column("engagement_generated_tasks", "assignee_staff_id")
    op.drop_column("engagement_generated_tasks", "parent_task_id")
