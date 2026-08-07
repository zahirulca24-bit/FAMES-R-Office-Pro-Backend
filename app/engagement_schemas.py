from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EngagementCreateRequest(BaseModel):
    client_id: str
    service_type: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=300)
    period_start: date | None = None
    period_end: date | None = None
    partner_user_id: str
    manager_user_id: str | None = None
    priority: str = Field(default="NORMAL", max_length=30)
    deadline: date | None = None
    fee_currency: str = Field(default="BDT", min_length=3, max_length=3)
    agreed_fee_minor: int | None = Field(default=None, ge=0)
    budget_minutes: int | None = Field(default=None, ge=0)
    confidentiality_level: str = Field(default="INTERNAL", max_length=30)

    @field_validator("service_type", "priority", "fee_currency", "confidentiality_level")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_period(self) -> "EngagementCreateRequest":
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class EngagementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    service_type: str | None = Field(default=None, min_length=2, max_length=80)
    period_start: date | None = None
    period_end: date | None = None
    partner_user_id: str | None = None
    manager_user_id: str | None = None
    priority: str | None = Field(default=None, max_length=30)
    deadline: date | None = None
    fee_currency: str | None = Field(default=None, min_length=3, max_length=3)
    agreed_fee_minor: int | None = Field(default=None, ge=0)
    budget_minutes: int | None = Field(default=None, ge=0)
    confidentiality_level: str | None = Field(default=None, max_length=30)
    expected_version: int = Field(ge=1)


class EngagementTeamAssignRequest(BaseModel):
    staff_id: str
    assignment_role: str = Field(default="TEAM_MEMBER", max_length=40)
    starts_on: date | None = None
    ends_on: date | None = None

    @field_validator("assignment_role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_dates(self) -> "EngagementTeamAssignRequest":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        return self


class EngagementTeamMemberView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    engagement_id: str
    staff_id: str
    assignment_role: str
    status: str
    starts_on: date | None
    ends_on: date | None
    created_at: datetime


class EngagementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    engagement_code: str
    client_id: str
    service_type: str
    title: str
    period_start: date | None
    period_end: date | None
    partner_user_id: str
    manager_user_id: str | None
    status: str
    priority: str
    deadline: date | None
    fee_currency: str
    agreed_fee_minor: int | None
    budget_minutes: int | None
    confidentiality_level: str
    version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class EngagementDetail(EngagementView):
    team: list[EngagementTeamMemberView]


class EngagementListResponse(BaseModel):
    items: list[EngagementView]
    page: int
    page_size: int
    total: int
