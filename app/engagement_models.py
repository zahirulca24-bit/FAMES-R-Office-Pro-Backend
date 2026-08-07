from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngagementNumberSequence(Base):
    __tablename__ = "engagement_number_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Engagement(Base):
    __tablename__ = "engagements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)
    service_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    partner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="RESTRICT"), nullable=False, index=True)
    manager_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT", index=True)
    priority: Mapped[str] = mapped_column(String(30), nullable=False, default="NORMAL", index=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fee_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    agreed_fee_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidentiality_level: Mapped[str] = mapped_column(String(30), nullable=False, default="INTERNAL", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class EngagementTeamMember(Base):
    __tablename__ = "engagement_team_members"
    __table_args__ = (UniqueConstraint("engagement_id", "staff_id", name="uq_engagement_team_staff"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    assignment_role: Mapped[str] = mapped_column(String(40), nullable=False, default="TEAM_MEMBER", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
