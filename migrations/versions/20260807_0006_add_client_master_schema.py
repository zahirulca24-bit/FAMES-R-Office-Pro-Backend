"""Add client master and linked records.

Revision ID: 20260807_0006
Revises: 20260807_0005
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260807_0006"
down_revision: str | None = "20260807_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_column() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "clients",
        _id_column(),
        sa.Column("client_code", sa.String(length=40), nullable=False),
        sa.Column("legal_name", sa.String(length=300), nullable=False),
        sa.Column("trading_name", sa.String(length=300), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("client_group", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PROSPECT"),
        sa.Column("confidentiality_level", sa.String(length=30), nullable=False, server_default="INTERNAL"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_code", name="uq_clients_client_code"),
    )
    for column in ("client_code", "legal_name", "trading_name", "entity_type", "industry", "client_group", "status", "is_archived"):
        op.create_index(f"ix_clients_{column}", "clients", [column])

    op.create_table(
        "client_contacts",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_type", sa.String(length=50), nullable=False, server_default="GENERAL"),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("designation", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_contacts_client_id", "client_contacts", ["client_id"])
    op.create_index("ix_client_contacts_email", "client_contacts", ["email"])
    op.create_index("ix_client_contacts_phone", "client_contacts", ["phone"])

    op.create_table(
        "client_addresses",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("address_type", sa.String(length=50), nullable=False, server_default="REGISTERED"),
        sa.Column("line1", sa.String(length=300), nullable=False),
        sa.Column("line2", sa.String(length=300), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=False, server_default="Bangladesh"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_addresses_client_id", "client_addresses", ["client_id"])

    op.create_table(
        "client_identifiers",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_type", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=160), nullable=False),
        sa.Column("normalized_value", sa.String(length=160), nullable=False),
        sa.Column("issued_by", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("identifier_type", "normalized_value", name="uq_client_identifier_type_value"),
        sa.UniqueConstraint("client_id", "identifier_type", name="uq_client_identifier_client_type"),
    )
    for column in ("client_id", "identifier_type", "normalized_value"):
        op.create_index(f"ix_client_identifiers_{column}", "client_identifiers", [column])

    op.create_table(
        "client_directors",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("designation", sa.String(length=120), nullable=True),
        sa.Column("national_id_reference", sa.String(length=120), nullable=True),
        sa.Column("appointed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ceased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_client_directors_client_id", "client_directors", ["client_id"])
    op.create_index("ix_client_directors_full_name", "client_directors", ["full_name"])

    op.create_table(
        "client_shareholders",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shareholder_name", sa.String(length=250), nullable=False),
        sa.Column("shareholder_type", sa.String(length=40), nullable=False, server_default="INDIVIDUAL"),
        sa.Column("ownership_percent", sa.Numeric(7, 4), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_client_shareholders_client_id", "client_shareholders", ["client_id"])
    op.create_index("ix_client_shareholders_shareholder_name", "client_shareholders", ["shareholder_name"])

    op.create_table(
        "client_relationships",
        _id_column(),
        sa.Column("source_client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_client_id", "target_client_id", "relationship_type", name="uq_client_relationship"),
    )
    for column in ("source_client_id", "target_client_id", "relationship_type"):
        op.create_index(f"ix_client_relationships_{column}", "client_relationships", [column])

    op.create_table(
        "client_status_history",
        _id_column(),
        sa.Column("client_id", sa.String(length=36), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("changed_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("client_id", "to_status", "correlation_id", "changed_at"):
        op.create_index(f"ix_client_status_history_{column}", "client_status_history", [column])


def downgrade() -> None:
    op.drop_table("client_status_history")
    op.drop_table("client_relationships")
    op.drop_table("client_shareholders")
    op.drop_table("client_directors")
    op.drop_table("client_identifiers")
    op.drop_table("client_addresses")
    op.drop_table("client_contacts")
    op.drop_table("clients")
