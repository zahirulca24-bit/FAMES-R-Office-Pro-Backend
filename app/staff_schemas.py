from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StaffSkillInput(BaseModel):
    skill_code: str = Field(min_length=1, max_length=80)
    skill_name: str = Field(min_length=2, max_length=160)
    proficiency_level: str = Field(default="WORKING", max_length=30)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("skill_code", "proficiency_level")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class StaffCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    auth_user_id: str | None = None
    department_id: str | None = None
    designation_id: str | None = None
    supervisor_staff_id: str | None = None
    employment_type: str = Field(default="PERMANENT", max_length=40)
    join_date: date | None = None
    confidentiality_level: str = Field(default="INTERNAL", max_length=30)
    skills: list[StaffSkillInput] = Field(default_factory=list, max_length=30)

    @field_validator("employment_type", "confidentiality_level")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class StaffUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    department_id: str | None = None
    designation_id: str | None = None
    supervisor_staff_id: str | None = None
    employment_type: str | None = Field(default=None, max_length=40)
    employment_status: str | None = Field(default=None, max_length=30)
    end_date: date | None = None
    confidentiality_level: str | None = Field(default=None, max_length=30)
    expected_version: int = Field(ge=1)


class StaffSkillView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    skill_code: str
    skill_name: str
    proficiency_level: str
    notes: str | None
    is_active: bool


class StaffView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    staff_code: str
    auth_user_id: str | None
    full_name: str
    email: str | None
    phone: str | None
    department_id: str | None
    designation_id: str | None
    supervisor_staff_id: str | None
    employment_type: str
    employment_status: str
    join_date: date | None
    end_date: date | None
    confidentiality_level: str
    version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class StaffDetail(StaffView):
    skills: list[StaffSkillView]


class StaffListResponse(BaseModel):
    items: list[StaffView]
    page: int
    page_size: int
    total: int


class DepartmentCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class DepartmentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    status: str


class DesignationCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    department_id: str | None = None
    rank_order: int = Field(default=100, ge=1, le=10000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class DesignationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    department_id: str | None
    rank_order: int
    status: str
