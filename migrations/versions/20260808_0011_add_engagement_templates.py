"""Add engagement templates and generated task/document records.

Revision ID: 20260808_0011
Revises: 20260808_0010
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0011"
down_revision = "20260808_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("service_type", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_engagement_template_code"),
    )
    op.create_index("ix_engagement_templates_code", "engagement_templates", ["code"])
    op.create_index("ix_engagement_templates_service_type", "engagement_templates", ["service_type"])
    op.create_index("ix_engagement_templates_status", "engagement_templates", ["status"])

    op.create_table(
        "engagement_template_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("engagement_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_code", sa.String(60), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_offset_days", sa.Integer(), nullable=True),
        sa.Column("default_assignment_role", sa.String(40), nullable=True),
        sa.Column("approval_role", sa.String(40), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("template_id", "task_code", name="uq_engagement_template_task_code"),
    )
    op.create_index("ix_engagement_template_tasks_template_id", "engagement_template_tasks", ["template_id"])
    op.create_index("ix_engagement_template_tasks_stage", "engagement_template_tasks", ["stage"])

    op.create_table(
        "engagement_template_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("engagement_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_code", sa.String(60), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("template_id", "document_code", name="uq_engagement_template_document_code"),
    )
    op.create_index("ix_engagement_template_documents_template_id", "engagement_template_documents", ["template_id"])
    op.create_index("ix_engagement_template_documents_stage", "engagement_template_documents", ["stage"])

    op.create_table(
        "engagement_generated_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_task_id", sa.String(36), sa.ForeignKey("engagement_template_tasks.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("task_code", sa.String(60), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("assignment_role", sa.String(40), nullable=True),
        sa.Column("approval_role", sa.String(40), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "template_task_id", name="uq_generated_task_engagement_template_task"),
    )
    op.create_index("ix_engagement_generated_tasks_engagement_id", "engagement_generated_tasks", ["engagement_id"])
    op.create_index("ix_engagement_generated_tasks_task_code", "engagement_generated_tasks", ["task_code"])
    op.create_index("ix_engagement_generated_tasks_stage", "engagement_generated_tasks", ["stage"])
    op.create_index("ix_engagement_generated_tasks_due_date", "engagement_generated_tasks", ["due_date"])
    op.create_index("ix_engagement_generated_tasks_status", "engagement_generated_tasks", ["status"])

    op.create_table(
        "engagement_required_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_document_id", sa.String(36), sa.ForeignKey("engagement_template_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_code", sa.String(60), nullable=False),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "template_document_id", name="uq_required_doc_engagement_template_doc"),
    )
    op.create_index("ix_engagement_required_documents_engagement_id", "engagement_required_documents", ["engagement_id"])
    op.create_index("ix_engagement_required_documents_document_code", "engagement_required_documents", ["document_code"])
    op.create_index("ix_engagement_required_documents_stage", "engagement_required_documents", ["stage"])
    op.create_index("ix_engagement_required_documents_status", "engagement_required_documents", ["status"])


def downgrade() -> None:
    op.drop_table("engagement_required_documents")
    op.drop_table("engagement_generated_tasks")
    op.drop_table("engagement_template_documents")
    op.drop_table("engagement_template_tasks")
    op.drop_table("engagement_templates")
