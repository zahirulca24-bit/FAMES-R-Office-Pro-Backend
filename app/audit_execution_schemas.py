from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RequisitionCreateRequest(BaseModel):
    requisition_code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=3, max_length=300)
    requested_from: str | None = Field(default=None, max_length=200)
    due_date: date | None = None

    @field_validator("requisition_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class RequisitionStatusRequest(BaseModel):
    expected_version: int = Field(ge=1)
    status: str
    response_note: str | None = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"OPEN", "RECEIVED", "CLOSED"}:
            raise ValueError("status must be OPEN, RECEIVED or CLOSED")
        return value


class RequisitionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    requisition_code: str
    title: str
    requested_from: str | None
    due_date: date | None
    status: str
    response_note: str | None
    version: int
    received_at: datetime | None
    created_at: datetime


class AuditTestCreateRequest(BaseModel):
    test_code: str = Field(min_length=2, max_length=60)
    description: str = Field(min_length=3)
    risk_id: str | None = None
    working_paper_id: str | None = None
    sample_size: int = Field(default=0, ge=0)

    @field_validator("test_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class AuditTestCompleteRequest(BaseModel):
    expected_version: int = Field(ge=1)
    exceptions_count: int = Field(ge=0)
    conclusion: str = Field(min_length=3)


class AuditTestView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    risk_id: str | None
    working_paper_id: str | None
    test_code: str
    description: str
    sample_size: int
    exceptions_count: int
    conclusion: str | None
    status: str
    version: int
    completed_at: datetime | None


class AuditIssueCreateRequest(BaseModel):
    issue_code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=3, max_length=300)
    severity: str = "MEDIUM"
    description: str = Field(min_length=3)
    risk_id: str | None = None

    @field_validator("issue_code", "severity")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        value = value.strip().upper()
        if value in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} or not value.startswith(("LOW", "MEDIUM", "HIGH", "CRITICAL")):
            return value
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        if value not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("invalid severity")
        return value


class AuditIssueResolveRequest(BaseModel):
    expected_version: int = Field(ge=1)
    resolution: str = Field(min_length=3)


class AuditIssueView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    risk_id: str | None
    issue_code: str
    title: str
    severity: str
    description: str
    status: str
    resolution: str | None
    version: int
    resolved_at: datetime | None


class CompletionUpsertRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    subsequent_events_done: bool = False
    going_concern_done: bool = False
    misstatements_evaluated: bool = False
    representation_letter_obtained: bool = False
    quality_review_done: bool = False


class CompletionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    subsequent_events_done: bool
    going_concern_done: bool
    misstatements_evaluated: bool
    representation_letter_obtained: bool
    quality_review_done: bool
    status: str
    version: int
    is_locked: bool
    finalized_by_user_id: str | None
    finalized_at: datetime | None


class FinalizationReadinessView(BaseModel):
    engagement_id: str
    ready: bool
    planning_ready: bool
    completion_checklist_ready: bool
    open_requisitions: int
    incomplete_tests: int
    open_high_risk_issues: int
    open_other_issues: int
    unlocked_working_papers: int
    significant_risks_without_procedure: int


class CompletionActionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    action: str
    actor_user_id: str | None
    detail_json: str | None
    created_at: datetime
