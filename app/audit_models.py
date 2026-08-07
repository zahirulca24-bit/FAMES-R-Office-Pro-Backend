from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditAcceptance(Base):
    __tablename__ = "audit_acceptance"
    __table_args__ = (UniqueConstraint("engagement_id", name="uq_audit_acceptance_engagement"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    continuance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integrity_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    competence_resources: Mapped[str | None] = mapped_column(Text, nullable=True)
    preconditions_met: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AuditIndependenceDeclaration(Base):
    __tablename__ = "audit_independence_declarations"
    __table_args__ = (UniqueConstraint("engagement_id", "staff_id", name="uq_audit_independence_staff"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CLEAR", index=True)
    threat_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    safeguards: Mapped[str | None] = mapped_column(Text, nullable=True)
    declared_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AuditMateriality(Base):
    __tablename__ = "audit_materiality"
    __table_args__ = (UniqueConstraint("engagement_id", name="uq_audit_materiality_engagement"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    benchmark: Mapped[str] = mapped_column(String(100), nullable=False)
    benchmark_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    percentage_basis_points: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_materiality_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    performance_materiality_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    trivial_threshold_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AuditRisk(Base):
    __tablename__ = "audit_risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    engagement_id: Mapped[str] = mapped_column(String(36), ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assertion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    likelihood: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    impact: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    significant_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AuditRiskProcedure(Base):
    __tablename__ = "audit_risk_procedures"
    __table_args__ = (UniqueConstraint("risk_id", "working_paper_id", name="uq_audit_risk_working_paper"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    risk_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_risks.id", ondelete="CASCADE"), nullable=False, index=True)
    working_paper_id: Mapped[str] = mapped_column(String(36), ForeignKey("working_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    procedure_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
