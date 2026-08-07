from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False, default="GENERAL", index=True)
    confidentiality_level: Mapped[str] = mapped_column(String(30), nullable=False, default="INTERNAL", index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hex: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class DocumentAccessLog(Base):
    __tablename__ = "document_access_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False, default="SUCCESS", index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
