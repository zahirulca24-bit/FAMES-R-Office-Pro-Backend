from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClientContactInput(BaseModel):
    contact_type: str = Field(default="GENERAL", max_length=50)
    full_name: str = Field(min_length=2, max_length=200)
    designation: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    is_primary: bool = False


class ClientAddressInput(BaseModel):
    address_type: str = Field(default="REGISTERED", max_length=50)
    line1: str = Field(min_length=2, max_length=300)
    line2: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=30)
    country: str = Field(default="Bangladesh", max_length=120)
    is_primary: bool = False


class ClientIdentifierInput(BaseModel):
    identifier_type: str = Field(min_length=2, max_length=50)
    value: str = Field(min_length=1, max_length=160)
    issued_by: str | None = Field(default=None, max_length=160)

    @field_validator("identifier_type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return value.strip().upper()


class ClientCreateRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=300)
    trading_name: str | None = Field(default=None, max_length=300)
    entity_type: str = Field(min_length=2, max_length=80)
    industry: str | None = Field(default=None, max_length=120)
    client_group: str | None = Field(default=None, max_length=120)
    confidentiality_level: str = Field(default="INTERNAL", max_length=30)
    partner_user_id: str
    manager_user_id: str | None = None
    contacts: list[ClientContactInput] = Field(default_factory=list, max_length=20)
    addresses: list[ClientAddressInput] = Field(default_factory=list, max_length=20)
    identifiers: list[ClientIdentifierInput] = Field(default_factory=list, max_length=20)

    @field_validator("entity_type", "confidentiality_level")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class ClientUpdateRequest(BaseModel):
    legal_name: str | None = Field(default=None, min_length=2, max_length=300)
    trading_name: str | None = Field(default=None, max_length=300)
    entity_type: str | None = Field(default=None, min_length=2, max_length=80)
    industry: str | None = Field(default=None, max_length=120)
    client_group: str | None = Field(default=None, max_length=120)
    confidentiality_level: str | None = Field(default=None, max_length=30)
    expected_version: int = Field(ge=1)


class ClientArchiveRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    expected_version: int = Field(ge=1)


class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_code: str
    legal_name: str
    trading_name: str | None
    entity_type: str
    industry: str | None
    client_group: str | None
    status: str
    confidentiality_level: str
    version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ClientContactView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    contact_type: str
    full_name: str
    designation: str | None
    email: str | None
    phone: str | None
    is_primary: bool
    is_active: bool


class ClientAddressView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    address_type: str
    line1: str
    line2: str | None
    city: str | None
    district: str | None
    postal_code: str | None
    country: str
    is_primary: bool


class ClientIdentifierView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    identifier_type: str
    value: str
    issued_by: str | None


class ClientDetail(ClientSummary):
    contacts: list[ClientContactView]
    addresses: list[ClientAddressView]
    identifiers: list[ClientIdentifierView]


class ClientListResponse(BaseModel):
    items: list[ClientSummary]
    page: int
    page_size: int
    total: int


class ClientActivityView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_type: str
    summary: str
    detail_json: str | None
    created_at: datetime
