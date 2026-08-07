from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AcceptanceUpsertRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    continuance: bool = False
    integrity_assessment: str | None = None
    competence_resources: str | None = None
    preconditions_met: bool = False
    reason: str | None = None


class AcceptanceDecisionRequest(BaseModel):
    expected_version: int = Field(ge=1)
    decision: str
    reason: str | None = None

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"APPROVED", "REJECTED"}:
            raise ValueError("decision must be APPROVED or REJECTED")
        return value


class IndependenceUpsertRequest(BaseModel):
    staff_id: str
    status: str = "CLEAR"
    threat_details: str | None = None
    safeguards: str | None = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"CLEAR", "THREAT", "NOT_INDEPENDENT"}:
            raise ValueError("invalid independence status")
        return value


class MaterialityUpsertRequest(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    benchmark: str = Field(min_length=2, max_length=100)
    benchmark_amount_minor: int = Field(gt=0)
    percentage_basis_points: int = Field(gt=0, le=10000)
    overall_materiality_minor: int = Field(gt=0)
    performance_materiality_minor: int = Field(gt=0)
    trivial_threshold_minor: int = Field(ge=0)
    rationale: str | None = None


class RiskCreateRequest(BaseModel):
    risk_code: str = Field(min_length=2, max_length=60)
    area: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=3)
    assertion: str | None = Field(default=None, max_length=120)
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    significant_risk: bool = False
    response_summary: str | None = None

    @field_validator("risk_code", "area")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class RiskProcedureLinkRequest(BaseModel):
    working_paper_id: str
    procedure_note: str | None = None


class AcceptanceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    status: str
    continuance: bool
    integrity_assessment: str | None
    competence_resources: str | None
    preconditions_met: bool
    reason: str | None
    version: int
    approved_by_user_id: str | None
    approved_at: datetime | None


class IndependenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    staff_id: str
    status: str
    threat_details: str | None
    safeguards: str | None
    declared_at: datetime


class MaterialityView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    benchmark: str
    benchmark_amount_minor: int
    percentage_basis_points: int
    overall_materiality_minor: int
    performance_materiality_minor: int
    trivial_threshold_minor: int
    rationale: str | None
    version: int


class RiskView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    risk_code: str
    area: str
    description: str
    assertion: str | None
    likelihood: int
    impact: int
    significant_risk: bool
    response_summary: str | None
    status: str


class PlanningReadinessView(BaseModel):
    engagement_id: str
    ready: bool
    acceptance_approved: bool
    independence_complete: bool
    materiality_set: bool
    open_independence_threats: int
    risks_count: int
    risks_without_procedure: int
