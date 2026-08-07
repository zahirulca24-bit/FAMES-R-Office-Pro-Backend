import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Designation(Base):
    __tablename__ = "designations"
    __table_args__ = (UniqueConstraint("department_id", "name", name="uq_designation_department_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    department_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    rank_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    staff_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    auth_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    designation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("designations.id", ondelete="SET NULL"), nullable=True, index=True)
    supervisor_staff_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    employment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PERMANENT", index=True)
    employment_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidentiality_level: Mapped[str] = mapped_column(String(30), nullable=False, default="INTERNAL")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class StaffSkill(Base):
    __tablename__ = "staff_skills"
    __table_args__ = (UniqueConstraint("staff_id", "skill_code", name="uq_staff_skill_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(160), nullable=False)
    proficiency_level: Mapped[str] = mapped_column(String(30), nullable=False, default="WORKING")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
