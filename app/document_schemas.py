from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version_number: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256_hex: str
    change_note: str | None
    created_at: datetime


class DocumentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_code: str
    resource_type: str
    resource_id: str
    title: str
    document_type: str
    confidentiality_level: str
    current_version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentView):
    versions: list[DocumentVersionView]


class DocumentListResponse(BaseModel):
    items: list[DocumentView]
    page: int
    page_size: int
    total: int


class DocumentArchiveRequest(BaseModel):
    expected_version: int = Field(ge=1)


class DocumentAccessLogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_user_id: str | None
    action: str
    outcome: str
    correlation_id: str
    created_at: datetime
