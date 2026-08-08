"""Add audit requisitions, tests, issues and completion/finalization controls.

Revision ID: 20260808_0017
Revises: 20260808_0016
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0017"
down_revision = "20260808_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_requisitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requisition_code", sa.String(60), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("requested_from", sa.String(200), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "requisition_code", name="uq_audit_requisition_code"),
    )
    op.create_index("ix_audit_requisitions_engagement_id", "audit_requisitions", ["engagement_id"])
    op.create_index("ix_audit_requisitions_requisition_code", "audit_requisitions", ["requisition_code"])
    op.create_index("ix_audit_requisitions_due_date", "audit_requisitions", ["due_date"])
    op.create_index("ix_audit_requisitions_status", "audit_requisitions", ["status"])

    op.create_table(
        "audit_tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_id", sa.String(36), sa.ForeignKey("audit_risks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("working_paper_id", sa.String(36), sa.ForeignKey("working_papers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("test_code", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("exceptions_count", sa.Integer(), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("performed_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "test_code", name="uq_audit_test_code"),
    )
    op.create_index("ix_audit_tests_engagement_id", "audit_tests", ["engagement_id"])
    op.create_index("ix_audit_tests_risk_id", "audit_tests", ["risk_id"])
    op.create_index("ix_audit_tests_working_paper_id", "audit_tests", ["working_paper_id"])
    op.create_index("ix_audit_tests_test_code", "audit_tests", ["test_code"])
    op.create_index("ix_audit_tests_status", "audit_tests", ["status"])

    op.create_table(
        "audit_issues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_id", sa.String(36), sa.ForeignKey("audit_risks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("issue_code", sa.String(60), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("raised_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "issue_code", name="uq_audit_issue_code"),
    )
    op.create_index("ix_audit_issues_engagement_id", "audit_issues", ["engagement_id"])
    op.create_index("ix_audit_issues_risk_id", "audit_issues", ["risk_id"])
    op.create_index("ix_audit_issues_issue_code", "audit_issues", ["issue_code"])
    op.create_index("ix_audit_issues_severity", "audit_issues", ["severity"])
    op.create_index("ix_audit_issues_status", "audit_issues", ["status"])

    op.create_table(
        "audit_completion",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subsequent_events_done", sa.Boolean(), nullable=False),
        sa.Column("going_concern_done", sa.Boolean(), nullable=False),
        sa.Column("misstatements_evaluated", sa.Boolean(), nullable=False),
        sa.Column("representation_letter_obtained", sa.Boolean(), nullable=False),
        sa.Column("quality_review_done", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("finalized_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", name="uq_audit_completion_engagement"),
    )
    op.create_index("ix_audit_completion_engagement_id", "audit_completion", ["engagement_id"])
    op.create_index("ix_audit_completion_status", "audit_completion", ["status"])
    op.create_index("ix_audit_completion_is_locked", "audit_completion", ["is_locked"])

    op.create_table(
        "audit_completion_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_completion_actions_engagement_id", "audit_completion_actions", ["engagement_id"])
    op.create_index("ix_audit_completion_actions_action", "audit_completion_actions", ["action"])
    op.create_index("ix_audit_completion_actions_created_at", "audit_completion_actions", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_completion_actions")
    op.drop_table("audit_completion")
    op.drop_table("audit_issues")
    op.drop_table("audit_tests")
    op.drop_table("audit_requisitions")
