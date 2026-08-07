"""Add engagement core, numbering and team assignment.

Revision ID: 20260808_0010
Revises: 20260808_0009
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0010"
down_revision = "20260808_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement_number_sequences",
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "engagements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_code", sa.String(40), nullable=False, unique=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("partner_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("manager_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(30), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("fee_currency", sa.String(3), nullable=False),
        sa.Column("agreed_fee_minor", sa.Integer(), nullable=True),
        sa.Column("budget_minutes", sa.Integer(), nullable=True),
        sa.Column("confidentiality_level", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_engagements_engagement_code", "engagements", ["engagement_code"], unique=True)
    op.create_index("ix_engagements_client_id", "engagements", ["client_id"])
    op.create_index("ix_engagements_service_type", "engagements", ["service_type"])
    op.create_index("ix_engagements_partner_user_id", "engagements", ["partner_user_id"])
    op.create_index("ix_engagements_manager_user_id", "engagements", ["manager_user_id"])
    op.create_index("ix_engagements_status", "engagements", ["status"])
    op.create_index("ix_engagements_priority", "engagements", ["priority"])
    op.create_index("ix_engagements_deadline", "engagements", ["deadline"])
    op.create_index("ix_engagements_confidentiality_level", "engagements", ["confidentiality_level"])
    op.create_index("ix_engagements_is_archived", "engagements", ["is_archived"])

    op.create_table(
        "engagement_team_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assignment_role", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("assigned_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("engagement_id", "staff_id", name="uq_engagement_team_staff"),
    )
    op.create_index("ix_engagement_team_members_engagement_id", "engagement_team_members", ["engagement_id"])
    op.create_index("ix_engagement_team_members_staff_id", "engagement_team_members", ["staff_id"])
    op.create_index("ix_engagement_team_members_assignment_role", "engagement_team_members", ["assignment_role"])
    op.create_index("ix_engagement_team_members_status", "engagement_team_members", ["status"])


def downgrade() -> None:
    op.drop_table("engagement_team_members")
    op.drop_table("engagements")
    op.drop_table("engagement_number_sequences")
