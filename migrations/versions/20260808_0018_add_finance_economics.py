"""Add finance invoices, receipts, expenses and finance actions.

Revision ID: 20260808_0018
Revises: 20260808_0017
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0018"
down_revision = "20260808_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finance_invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_number", sa.String(60), nullable=False),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal_minor", sa.Integer(), nullable=False),
        sa.Column("vat_minor", sa.Integer(), nullable=False),
        sa.Column("tax_minor", sa.Integer(), nullable=False),
        sa.Column("total_minor", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("invoice_number", name="uq_finance_invoice_number"),
    )
    op.create_index("ix_finance_invoices_invoice_number", "finance_invoices", ["invoice_number"])
    op.create_index("ix_finance_invoices_engagement_id", "finance_invoices", ["engagement_id"])
    op.create_index("ix_finance_invoices_due_date", "finance_invoices", ["due_date"])
    op.create_index("ix_finance_invoices_status", "finance_invoices", ["status"])

    op.create_table(
        "finance_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_number", sa.String(60), nullable=False),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("finance_invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(40), nullable=False),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("receipt_number", name="uq_finance_receipt_number"),
    )
    op.create_index("ix_finance_receipts_receipt_number", "finance_receipts", ["receipt_number"])
    op.create_index("ix_finance_receipts_invoice_id", "finance_receipts", ["invoice_id"])
    op.create_index("ix_finance_receipts_received_on", "finance_receipts", ["received_on"])

    op.create_table(
        "engagement_expenses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("incurred_on", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("recorded_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_engagement_expenses_engagement_id", "engagement_expenses", ["engagement_id"])
    op.create_index("ix_engagement_expenses_category", "engagement_expenses", ["category"])
    op.create_index("ix_engagement_expenses_incurred_on", "engagement_expenses", ["incurred_on"])
    op.create_index("ix_engagement_expenses_status", "engagement_expenses", ["status"])

    op.create_table(
        "finance_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_finance_actions_engagement_id", "finance_actions", ["engagement_id"])
    op.create_index("ix_finance_actions_resource_type", "finance_actions", ["resource_type"])
    op.create_index("ix_finance_actions_resource_id", "finance_actions", ["resource_id"])
    op.create_index("ix_finance_actions_action", "finance_actions", ["action"])
    op.create_index("ix_finance_actions_created_at", "finance_actions", ["created_at"])


def downgrade() -> None:
    op.drop_table("finance_actions")
    op.drop_table("engagement_expenses")
    op.drop_table("finance_receipts")
    op.drop_table("finance_invoices")
