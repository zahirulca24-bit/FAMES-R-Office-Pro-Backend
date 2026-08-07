from __future__ import annotations

from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TemplateTaskInput(BaseModel):
    task_code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=250)
    stage: str = Field(default="GENERAL", max_length=80)
    sequence: int = Field(default=100, ge=0)
    due_offset_days: int | None = Field(default=None, ge=0, le=3650)
    default_assignment_role: str | None = Field(default=None, max_length=40)
    approval_role: str | None = Field(default=None, max_length=40)
    required: bool = True

    @field_validator("task_code", "stage")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class TemplateDocumentInput(BaseModel):
    document_code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=250)
    stage: str = Field(default="GENERAL", max_length=80)
    required: bool = True

    @field_validator("document_code", "stage")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class EngagementTemplateCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=200)
    service_type: str = Field(min_length=2, max_length=80)
    description: str | None = None
    tasks: list[TemplateTaskInput] = Field(default_factory=list, max_length=200)
    required_documents: list[TemplateDocumentInput] = Field(default_factory=list, max_length=100)

    @field_validator("code", "service_type")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class EngagementTemplateView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    name: str
    service_type: str
    description: str | None
    status: str
    version: int


class EngagementTemplateApplyRequest(BaseModel):
    template_id: str
    expected_engagement_version: int = Field(ge=1)
    anchor_date: date | None = None


class GeneratedTaskView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    task_code: str
    title: str
    stage: str
    sequence: int
    due_date: date | None
    assignment_role: str | None
    approval_role: str | None
    status: str
    required: bool


class RequiredDocumentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    document_code: str
    title: str
    stage: str
    required: bool
    status: str


class TemplateApplyResult(BaseModel):
    engagement_id: str
    template_id: str
    generated_tasks: list[GeneratedTaskView]
    required_documents: list[RequiredDocumentView]
