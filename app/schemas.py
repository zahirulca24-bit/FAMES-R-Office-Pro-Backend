from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


ALLOWED_USER_ROLES = {
    "SUPER_ADMIN",
    "PARTNER",
    "MANAGER",
    "STUDENT",
    "CLIENT",
    "ASSISTANT_DEVELOPER",
}


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    login_id: str
    email: str | None
    full_name: str
    role: str
    status: str
    must_change_password: bool


class LoginRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=512)
    remember_me: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserView


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=10, max_length=512)


class AdminCreateUserRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=80)
    email: EmailStr | None = None
    full_name: str = Field(min_length=2, max_length=200)
    role: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=10, max_length=512)
    must_change_password: bool = True

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_USER_ROLES:
            raise ValueError("Unsupported user role")
        return normalized


class AdminStatusRequest(BaseModel):
    status: str
