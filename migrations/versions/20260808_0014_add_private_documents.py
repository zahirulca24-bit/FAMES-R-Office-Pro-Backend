"""Add private documents, versions and access logs.

Revision ID: 20260808_0014
Revises: 20260808_0013
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0014"
down_revision = "20260808_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_code", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("confidentiality_level", sa.String(30), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_code", name="uq_documents_document_code"),
    )
    op.create_index("ix_documents_document_code", "documents", ["document_code"])
    op.create_index("ix_documents_resource_type", "documents", ["resource_type"])
    op.create_index("ix_documents_resource_id", "documents", ["resource_id"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_confidentiality_level", "documents", ["confidentiality_level"])
    op.create_index("ix_documents_is_archived", "documents", ["is_archived"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hex", sa.String(64), nullable=False),
        sa.Column("content_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_sha256_hex", "document_versions", ["sha256_hex"])
    op.create_index("ix_document_versions_created_at", "document_versions", ["created_at"])

    op.create_table(
        "document_access_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_access_logs_document_id", "document_access_logs", ["document_id"])
    op.create_index("ix_document_access_logs_document_version_id", "document_access_logs", ["document_version_id"])
    op.create_index("ix_document_access_logs_actor_user_id", "document_access_logs", ["actor_user_id"])
    op.create_index("ix_document_access_logs_action", "document_access_logs", ["action"])
    op.create_index("ix_document_access_logs_outcome", "document_access_logs", ["outcome"])
    op.create_index("ix_document_access_logs_correlation_id", "document_access_logs", ["correlation_id"])
    op.create_index("ix_document_access_logs_created_at", "document_access_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("document_access_logs")
    op.drop_table("document_versions")
    op.drop_table("documents")
