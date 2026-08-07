from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkingPaper(Base):
    __tablename__ = "working_papers"
    __table_args__ = (UniqueConstraint("engagement_id", "paper_code", name="uq_working_paper_engagement_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False, default="GENERAL", index=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prepared_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    locked_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class WorkingPaperEvidence(Base):
    __tablename__ = "working_paper_evidence"
    __table_args__ = (UniqueConstraint("working_paper_id", "document_version_id", name="uq_working_paper_evidence_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    working_paper_id: Mapped[str] = mapped_column(String(36), ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_role: Mapped[str] = mapped_column(String(50), nullable=False, default="SUPPORTING", index=True)
    assertion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class WorkingPaperReviewNote(Base):
    __tablename__ = "working_paper_review_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    working_paper_id: Mapped[str] = mapped_column(String(36), ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    raised_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class WorkingPaperSignoff(Base):
    """Append-only working-paper preparation/review/approval/lock history."""

    __tablename__ = "working_paper_signoffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    working_paper_id: Mapped[str] = mapped_column(String(36), ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(30), nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
