"""Add record-level access control tables.

Revision ID: 20260806_0004
Revises: 20260806_0003
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260806_0004"
down_revision: str | None = "20260806_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_column() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "firm_memberships",
        _id_column(),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("firm_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "firm_code", name="uq_firm_membership_user_firm"),
    )
    op.create_index("ix_firm_memberships_user_id", "firm_memberships", ["user_id"])
    op.create_index("ix_firm_memberships_firm_code", "firm_memberships", ["firm_code"])
    op.create_index("ix_firm_memberships_status", "firm_memberships", ["status"])

    op.create_table(
        "portfolio_access_grants",
        _id_column(),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_key", sa.String(length=100), nullable=False),
        sa.Column("access_level", sa.String(length=30), nullable=False, server_default="READ"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("granted_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "portfolio_key", name="uq_portfolio_grant_user_key"),
    )
    op.create_index("ix_portfolio_access_grants_user_id", "portfolio_access_grants", ["user_id"])
    op.create_index("ix_portfolio_access_grants_portfolio_key", "portfolio_access_grants", ["portfolio_key"])
    op.create_index("ix_portfolio_access_grants_status", "portfolio_access_grants", ["status"])

    op.create_table(
        "engagement_access_grants",
        _id_column(),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("engagement_key", sa.String(length=100), nullable=False),
        sa.Column("assignment_role", sa.String(length=50), nullable=False, server_default="TEAM_MEMBER"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "engagement_key", name="uq_engagement_grant_user_key"),
    )
    op.create_index("ix_engagement_access_grants_user_id", "engagement_access_grants", ["user_id"])
    op.create_index("ix_engagement_access_grants_engagement_key", "engagement_access_grants", ["engagement_key"])
    op.create_index("ix_engagement_access_grants_status", "engagement_access_grants", ["status"])

    op.create_table(
        "confidentiality_grants",
        _id_column(),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("granted_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "resource_type", "resource_id", name="uq_confidentiality_grant_resource"),
    )
    op.create_index("ix_confidentiality_grants_user_id", "confidentiality_grants", ["user_id"])
    op.create_index("ix_confidentiality_grants_resource_type", "confidentiality_grants", ["resource_type"])
    op.create_index("ix_confidentiality_grants_resource_id", "confidentiality_grants", ["resource_id"])
    op.create_index("ix_confidentiality_grants_status", "confidentiality_grants", ["status"])

    op.create_table(
        "delegated_access",
        _id_column(),
        sa.Column("delegator_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delegate_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_code", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=True),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("delegator_user_id", "delegate_user_id", "permission_code", "resource_type", "resource_id", "status"):
        op.create_index(f"ix_delegated_access_{column}", "delegated_access", [column])


def downgrade() -> None:
    op.drop_table("delegated_access")
    op.drop_table("confidentiality_grants")
    op.drop_table("engagement_access_grants")
    op.drop_table("portfolio_access_grants")
    op.drop_table("firm_memberships")
