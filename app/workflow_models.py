import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_workflow_definition_code_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkflowState(Base):
    __tablename__ = "workflow_states"
    __table_args__ = (UniqueConstraint("workflow_definition_id", "code", name="uq_workflow_state_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_definition_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"
    __table_args__ = (UniqueConstraint("workflow_definition_id", "code", name="uq_workflow_transition_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_definition_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    from_state: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    to_state: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    required_permission: Mapped[str] = mapped_column(String(120), nullable=False)
    allowed_roles_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_codes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_reason: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id", name="uq_workflow_instance_resource"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_definition_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_definitions.id", ondelete="RESTRICT"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_state: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class WorkflowAction(Base):
    """Append-only workflow/approval action history."""

    __tablename__ = "workflow_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_instance_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    transition_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    from_state: Mapped[str] = mapped_column(String(80), nullable=False)
    to_state: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    policy_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class RecordLock(Base):
    __tablename__ = "record_locks"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id", name="uq_record_lock_resource"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    locked_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopen_requested_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    reopen_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reopened_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
