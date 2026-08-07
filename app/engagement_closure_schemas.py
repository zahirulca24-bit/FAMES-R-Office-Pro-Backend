from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EngagementTransitionRequest(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=1000)


class EngagementCloseRequest(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=1000)


class EngagementReopenRequest(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=1000)


class EngagementBlockers(BaseModel):
    incomplete_required_tasks: int
    overdue_required_tasks: int
    pending_required_documents: int
    blockers: list[str]


class EngagementWorkflowView(BaseModel):
    engagement_id: str
    engagement_code: str
    status: str
    version: int
    lock_state: str
    revision_number: int
    blockers: EngagementBlockers


class EngagementReviewActionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    action_type: str
    from_status: str
    to_status: str
    reason: str | None
    actor_user_id: str | None
    correlation_id: str
    revision_number: int
