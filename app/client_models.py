import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(300), index=True, nullable=False)
    trading_name: Mapped[str | None] = mapped_column(String(300), index=True, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    client_group: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False, default="PROSPECT")
    confidentiality_level: Mapped[str] = mapped_column(String(30), nullable=False, default="INTERNAL")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class ClientContact(Base):
    __tablename__ = "client_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL")
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ClientAddress(Base):
    __tablename__ = "client_addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    address_type: Mapped[str] = mapped_column(String(50), nullable=False, default="REGISTERED")
    line1: Mapped[str] = mapped_column(String(300), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(300), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False, default="Bangladesh")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ClientIdentifier(Base):
    __tablename__ = "client_identifiers"
    __table_args__ = (
        UniqueConstraint("identifier_type", "normalized_value", name="uq_client_identifier_type_value"),
        UniqueConstraint("client_id", "identifier_type", name="uq_client_identifier_client_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    issued_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ClientDirector(Base):
    __tablename__ = "client_directors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    national_id_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    appointed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ceased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClientShareholder(Base):
    __tablename__ = "client_shareholders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    shareholder_name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    shareholder_type: Mapped[str] = mapped_column(String(40), nullable=False, default="INDIVIDUAL")
    ownership_percent: Mapped[float | None] = mapped_column(Numeric(7, 4), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClientRelationship(Base):
    __tablename__ = "client_relationships"
    __table_args__ = (
        UniqueConstraint("source_client_id", "target_client_id", "relationship_type", name="uq_client_relationship"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    target_client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ClientStatusHistory(Base):
    __tablename__ = "client_status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
