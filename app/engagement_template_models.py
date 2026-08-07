from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngagementTemplate(Base):
    __tablename__ = "engagement_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    service_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class EngagementTemplateTask(Base):
    __tablename__ = "engagement_template_tasks"
    __table_args__ = (UniqueConstraint("template_id", "task_code", name="uq_engagement_template_task_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagement_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    task_code: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False, default="GENERAL", index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    due_offset_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_assignment_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    approval_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EngagementTemplateDocument(Base):
    __tablename__ = "engagement_template_documents"
    __table_args__ = (UniqueConstraint("template_id", "document_code", name="uq_engagement_template_document_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagement_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    document_code: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False, default="GENERAL", index=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EngagementGeneratedTask(Base):
    __tablename__ = "engagement_generated_tasks"
    __table_args__ = (UniqueConstraint("engagement_id", "template_task_id", name="uq_generated_task_engagement_template_task"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    template_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagement_template_tasks.id", ondelete="RESTRICT"), nullable=False)
    task_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    assignment_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    approval_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_STARTED", index=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class EngagementRequiredDocument(Base):
    __tablename__ = "engagement_required_documents"
    __table_args__ = (UniqueConstraint("engagement_id", "template_document_id", name="uq_required_doc_engagement_template_doc"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    template_document_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagement_template_documents.id", ondelete="RESTRICT"), nullable=False)
    document_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    stage: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
