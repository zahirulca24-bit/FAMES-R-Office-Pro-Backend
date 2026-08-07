"""Add client lifecycle, conflict, risk, service and portfolio controls.

Revision ID: 20260807_0007
Revises: 20260807_0006
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260807_0007"
down_revision: str | None = "20260807_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_column() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "client_conflict_checks",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("checked_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conflict_found", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_conflict_checks_client_id", "client_conflict_checks", ["client_id"])
    op.create_index("ix_client_conflict_checks_status", "client_conflict_checks", ["status"])

    op.create_table(
        "client_risk_profiles",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_level", sa.String(length=30), nullable=False, server_default="MEDIUM"),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("integrity_risk", sa.String(length=30), nullable=True),
        sa.Column("financial_risk", sa.String(length=30), nullable=True),
        sa.Column("regulatory_risk", sa.String(length=30), nullable=True),
        sa.Column("complexity_risk", sa.String(length=30), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", name="uq_client_risk_profile_client"),
    )
    op.create_index("ix_client_risk_profiles_client_id", "client_risk_profiles", ["client_id"])
    op.create_index("ix_client_risk_profiles_risk_level", "client_risk_profiles", ["risk_level"])

    op.create_table(
        "client_services",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_code", sa.String(length=80), nullable=False),
        sa.Column("service_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("client_id", "service_code", name="uq_client_service_code"),
    )
    op.create_index("ix_client_services_client_id", "client_services", ["client_id"])
    op.create_index("ix_client_services_service_code", "client_services", ["service_code"])
    op.create_index("ix_client_services_status", "client_services", ["status"])

    op.create_table(
        "client_portfolio_ownership",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("partner_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("manager_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("assigned_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", name="uq_client_portfolio_ownership_client"),
    )
    op.create_index("ix_client_portfolio_ownership_client_id", "client_portfolio_ownership", ["client_id"])
    op.create_index("ix_client_portfolio_ownership_partner_user_id", "client_portfolio_ownership", ["partner_user_id"])
    op.create_index("ix_client_portfolio_ownership_manager_user_id", "client_portfolio_ownership", ["manager_user_id"])
    op.create_index("ix_client_portfolio_ownership_status", "client_portfolio_ownership", ["status"])

    op.create_table(
        "client_archive_events",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("prior_status", sa.String(length=30), nullable=False),
        sa.Column("resulting_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_archive_events_client_id", "client_archive_events", ["client_id"])
    op.create_index("ix_client_archive_events_action", "client_archive_events", ["action"])
    op.create_index("ix_client_archive_events_correlation_id", "client_archive_events", ["correlation_id"])
    op.create_index("ix_client_archive_events_created_at", "client_archive_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("client_archive_events")
    op.drop_table("client_portfolio_ownership")
    op.drop_table("client_services")
    op.drop_table("client_risk_profiles")
    op.drop_table("client_conflict_checks")
