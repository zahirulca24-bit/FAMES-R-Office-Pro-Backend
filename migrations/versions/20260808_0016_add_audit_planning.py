"""Add audit planning, acceptance, independence, materiality and risk.

Revision ID: 20260808_0016
Revises: 20260808_0015
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0016"
down_revision = "20260808_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_acceptance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("continuance", sa.Boolean(), nullable=False),
        sa.Column("integrity_assessment", sa.Text(), nullable=True),
        sa.Column("competence_resources", sa.Text(), nullable=True),
        sa.Column("preconditions_met", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", name="uq_audit_acceptance_engagement"),
    )
    op.create_index("ix_audit_acceptance_engagement_id", "audit_acceptance", ["engagement_id"])
    op.create_index("ix_audit_acceptance_status", "audit_acceptance", ["status"])

    op.create_table(
        "audit_independence_declarations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("threat_details", sa.Text(), nullable=True),
        sa.Column("safeguards", sa.Text(), nullable=True),
        sa.Column("declared_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "staff_id", name="uq_audit_independence_staff"),
    )
    op.create_index("ix_audit_independence_engagement_id", "audit_independence_declarations", ["engagement_id"])
    op.create_index("ix_audit_independence_staff_id", "audit_independence_declarations", ["staff_id"])
    op.create_index("ix_audit_independence_status", "audit_independence_declarations", ["status"])

    op.create_table(
        "audit_materiality",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("benchmark", sa.String(100), nullable=False),
        sa.Column("benchmark_amount_minor", sa.Integer(), nullable=False),
        sa.Column("percentage_basis_points", sa.Integer(), nullable=False),
        sa.Column("overall_materiality_minor", sa.Integer(), nullable=False),
        sa.Column("performance_materiality_minor", sa.Integer(), nullable=False),
        sa.Column("trivial_threshold_minor", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", name="uq_audit_materiality_engagement"),
    )
    op.create_index("ix_audit_materiality_engagement_id", "audit_materiality", ["engagement_id"])

    op.create_table(
        "audit_risks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_code", sa.String(60), nullable=False),
        sa.Column("area", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assertion", sa.String(120), nullable=True),
        sa.Column("likelihood", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("significant_risk", sa.Boolean(), nullable=False),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_risks_engagement_id", "audit_risks", ["engagement_id"])
    op.create_index("ix_audit_risks_risk_code", "audit_risks", ["risk_code"])
    op.create_index("ix_audit_risks_area", "audit_risks", ["area"])
    op.create_index("ix_audit_risks_significant_risk", "audit_risks", ["significant_risk"])
    op.create_index("ix_audit_risks_status", "audit_risks", ["status"])

    op.create_table(
        "audit_risk_procedures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("risk_id", sa.String(36), sa.ForeignKey("audit_risks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("working_paper_id", sa.String(36), sa.ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("procedure_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("risk_id", "working_paper_id", name="uq_audit_risk_working_paper"),
    )
    op.create_index("ix_audit_risk_procedures_risk_id", "audit_risk_procedures", ["risk_id"])
    op.create_index("ix_audit_risk_procedures_working_paper_id", "audit_risk_procedures", ["working_paper_id"])


def downgrade() -> None:
    op.drop_table("audit_risk_procedures")
    op.drop_table("audit_risks")
    op.drop_table("audit_materiality")
    op.drop_table("audit_independence_declarations")
    op.drop_table("audit_acceptance")
