from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkingPaperCreateRequest(BaseModel):
    engagement_id: str
    paper_code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=300)
    area: str = Field(default="GENERAL", max_length=100)
    objective: str | None = None
    conclusion: str | None = None

    @field_validator("paper_code", "area")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class EvidenceLinkRequest(BaseModel):
    document_id: str
    document_version_id: str
    expected_version: int = Field(ge=1)
    evidence_role: str = Field(default="SUPPORTING", max_length=50)
    assertion: str | None = Field(default=None, max_length=120)
    note: str | None = None

    @field_validator("evidence_role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.strip().upper()


class ReviewNoteCreateRequest(BaseModel):
    note_text: str = Field(min_length=3, max_length=4000)


class ReviewNoteResolveRequest(BaseModel):
    expected_version: int = Field(ge=1)
    resolution_note: str = Field(min_length=3, max_length=4000)


class SignoffRequest(BaseModel):
    expected_version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=4000)


class EvidenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    document_version_id: str
    evidence_role: str
    assertion: str | None
    note: str | None
    created_at: datetime


class ReviewNoteView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    note_text: str
    status: str
    raised_by_user_id: str | None
    resolved_by_user_id: str | None
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime


class SignoffView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    action: str
    from_status: str
    to_status: str
    actor_user_id: str | None
    comment: str | None
    created_at: datetime


class WorkingPaperView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    paper_code: str
    title: str
    area: str
    objective: str | None
    conclusion: str | None
    status: str
    version: int
    is_locked: bool
    prepared_by_user_id: str | None
    reviewed_by_user_id: str | None
    approved_by_user_id: str | None
    locked_by_user_id: str | None
    reviewed_at: datetime | None
    approved_at: datetime | None
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkingPaperDetail(WorkingPaperView):
    evidence: list[EvidenceView]
    review_notes: list[ReviewNoteView]
    signoffs: list[SignoffView]


class WorkingPaperListResponse(BaseModel):
    items: list[WorkingPaperView]
    total: int
