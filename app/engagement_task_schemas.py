from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskConfigureRequest(BaseModel):
    expected_version: int = Field(ge=1)
    parent_task_id: str | None = None
    assignee_staff_id: str | None = None
    reviewer_staff_id: str | None = None
    weight_points: int | None = Field(default=None, ge=1, le=10000)
    due_date: date | None = None


class TaskDependencyCreateRequest(BaseModel):
    depends_on_task_id: str
    dependency_type: str = Field(default="FINISH_TO_START", max_length=30)

    @field_validator("dependency_type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return value.strip().upper()


class TaskTransitionRequest(BaseModel):
    to_status: str = Field(min_length=2, max_length=30)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=500)
    progress_percent: int | None = Field(default=None, ge=0, le=100)

    @field_validator("to_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()


class TaskView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    engagement_id: str
    parent_task_id: str | None
    task_code: str
    title: str
    stage: str
    sequence: int
    due_date: date | None
    assignment_role: str | None
    approval_role: str | None
    assignee_staff_id: str | None
    reviewer_staff_id: str | None
    weight_points: int
    progress_percent: int
    status: str
    escalation_state: str
    required: bool
    version: int
    started_at: datetime | None
    completed_at: datetime | None
    escalated_at: datetime | None


class TaskDependencyView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    engagement_id: str
    task_id: str
    depends_on_task_id: str
    dependency_type: str


class TaskProgressSummary(BaseModel):
    engagement_id: str
    total_tasks: int
    completed_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    total_weight: int
    earned_weight: float
    weighted_progress_percent: float


class DeadlineScanResult(BaseModel):
    engagement_id: str
    escalated_task_ids: list[str]
    overdue_count: int
