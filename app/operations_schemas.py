from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationCreateRequest(BaseModel):
    event_key: str = Field(min_length=2, max_length=100)
    resource_type: str = Field(min_length=2, max_length=50)
    resource_id: str = Field(min_length=1, max_length=100)
    recipient_user_id: str | None = None
    subject: str = Field(min_length=2, max_length=250)
    body: str = Field(min_length=2, max_length=4000)
    channel: str = "IN_APP"

    @field_validator("event_key", "resource_type", "channel")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class NotificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_key: str
    resource_type: str
    resource_id: str
    recipient_user_id: str | None
    subject: str
    body: str
    status: str
    channel: str
    created_at: datetime
    delivered_at: datetime | None


class BackupVerificationRequest(BaseModel):
    backup_reference: str = Field(min_length=3, max_length=200)
    backup_status: str
    restore_test_status: str
    notes: str | None = None

    @field_validator("backup_status", "restore_test_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"SUCCESS", "FAILED"}:
            raise ValueError("status must be SUCCESS or FAILED")
        return value


class BackupVerificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    backup_reference: str
    backup_status: str
    restore_test_status: str
    notes: str | None
    verified_by_user_id: str | None
    verified_at: datetime


class ReadinessCheckRequest(BaseModel):
    check_key: str = Field(min_length=2, max_length=100)
    passed: bool
    evidence: str | None = None

    @field_validator("check_key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip().upper()


class ReadinessCheckView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    check_key: str
    passed: bool
    evidence: str | None
    checked_by_user_id: str | None
    checked_at: datetime


class ExecutiveDashboardView(BaseModel):
    active_clients: int
    active_engagements: int
    open_audit_issues: int
    approved_invoices_minor: int
    receipts_minor: int
    outstanding_minor: int
    pending_notifications: int


class ProductionReadinessView(BaseModel):
    ready: bool
    checks_total: int
    checks_passed: int
    backup_restore_verified: bool
    blockers: list[str]
