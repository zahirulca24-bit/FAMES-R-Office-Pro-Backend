"""Add working papers, evidence, review notes and sign-offs.

Revision ID: 20260808_0015
Revises: 20260808_0014
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0015"
down_revision = "20260808_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "working_papers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("area", sa.String(100), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prepared_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("locked_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "paper_code", name="uq_working_paper_engagement_code"),
    )
    op.create_index("ix_working_papers_engagement_id", "working_papers", ["engagement_id"])
    op.create_index("ix_working_papers_paper_code", "working_papers", ["paper_code"])
    op.create_index("ix_working_papers_area", "working_papers", ["area"])
    op.create_index("ix_working_papers_status", "working_papers", ["status"])
    op.create_index("ix_working_papers_is_locked", "working_papers", ["is_locked"])

    op.create_table(
        "working_paper_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("working_paper_id", sa.String(36), sa.ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_role", sa.String(50), nullable=False),
        sa.Column("assertion", sa.String(120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("added_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("working_paper_id", "document_version_id", name="uq_working_paper_evidence_version"),
    )
    op.create_index("ix_working_paper_evidence_working_paper_id", "working_paper_evidence", ["working_paper_id"])
    op.create_index("ix_working_paper_evidence_document_id", "working_paper_evidence", ["document_id"])
    op.create_index("ix_working_paper_evidence_document_version_id", "working_paper_evidence", ["document_version_id"])
    op.create_index("ix_working_paper_evidence_evidence_role", "working_paper_evidence", ["evidence_role"])

    op.create_table(
        "working_paper_review_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("working_paper_id", sa.String(36), sa.ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("raised_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_working_paper_review_notes_working_paper_id", "working_paper_review_notes", ["working_paper_id"])
    op.create_index("ix_working_paper_review_notes_status", "working_paper_review_notes", ["status"])
    op.create_index("ix_working_paper_review_notes_created_at", "working_paper_review_notes", ["created_at"])

    op.create_table(
        "working_paper_signoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("working_paper_id", sa.String(36), sa.ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=False),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_working_paper_signoffs_working_paper_id", "working_paper_signoffs", ["working_paper_id"])
    op.create_index("ix_working_paper_signoffs_action", "working_paper_signoffs", ["action"])
    op.create_index("ix_working_paper_signoffs_actor_user_id", "working_paper_signoffs", ["actor_user_id"])
    op.create_index("ix_working_paper_signoffs_created_at", "working_paper_signoffs", ["created_at"])


def downgrade() -> None:
    op.drop_table("working_paper_signoffs")
    op.drop_table("working_paper_review_notes")
    op.drop_table("working_paper_evidence")
    op.drop_table("working_papers")
