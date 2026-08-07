from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AttendanceCreateRequest(BaseModel):
    staff_id: str
    work_date: date
    status: str = "PRESENT"
    worked_minutes: int = Field(default=0, ge=0, le=1440)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()


class LeaveCreateRequest(BaseModel):
    staff_id: str
    leave_date: date
    leave_type: str = Field(min_length=2, max_length=40)
    leave_minutes: int = Field(default=480, ge=1, le=1440)
    status: str = "APPROVED"
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("leave_type", "status")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class CapacityAssignmentCreateRequest(BaseModel):
    staff_id: str
    work_date: date
    source_type: str = Field(min_length=2, max_length=40)
    source_id: str = Field(min_length=1, max_length=100)
    assigned_minutes: int = Field(ge=1, le=1440)
    billable: bool = True

    @field_validator("source_type")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        return value.strip().upper()


class WorklogCreateRequest(BaseModel):
    staff_id: str
    work_date: date
    resource_type: str = Field(min_length=2, max_length=40)
    resource_id: str = Field(min_length=1, max_length=100)
    minutes: int = Field(ge=1, le=1440)
    billable: bool = True
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("resource_type")
    @classmethod
    def normalize_resource(cls, value: str) -> str:
        return value.strip().upper()


class WorklogTransitionRequest(BaseModel):
    expected_version: int = Field(ge=1)


class WorkforceRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    staff_id: str
    created_at: datetime


class AttendanceView(WorkforceRecordView):
    work_date: date
    status: str
    worked_minutes: int
    notes: str | None


class LeaveView(WorkforceRecordView):
    leave_date: date
    leave_type: str
    leave_minutes: int
    status: str
    reason: str | None


class CapacityAssignmentView(WorkforceRecordView):
    work_date: date
    source_type: str
    source_id: str
    assigned_minutes: int
    billable: bool


class WorklogView(WorkforceRecordView):
    work_date: date
    resource_type: str
    resource_id: str
    minutes: int
    billable: bool
    description: str | None
    status: str
    version: int
    reviewed_by_user_id: str | None
    reviewed_at: datetime | None
    locked_at: datetime | None


class CapacitySummary(BaseModel):
    staff_id: str
    work_date: date
    standard_minutes: int
    approved_leave_minutes: int
    available_minutes: int
    assigned_minutes: int
    logged_minutes: int
    remaining_minutes: int
    utilization_percent: float
