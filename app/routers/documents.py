from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.client_lifecycle_models import ClientPortfolioOwnership
from app.client_models import Client
from app.db import get_db
from app.deps import require_password_changed
from app.document_models import Document, DocumentAccessLog, DocumentVersion
from app.document_schemas import DocumentAccessLogView, DocumentDetail, DocumentListResponse, DocumentVersionView, DocumentView
from app.engagement_models import Engagement, EngagementTeamMember
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
_MAX_FILE_BYTES = 25 * 1024 * 1024
_ALLOWED_RESOURCE_TYPES = {"CLIENT", "ENGAGEMENT"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _can_access_resource(db: Session, user: AuthUser, resource_type: str, resource_id: str) -> bool:
    if user.role == "SUPER_ADMIN":
        return True
    if resource_type == "CLIENT":
        client = db.get(Client, resource_id)
        if client is None or client.is_archived:
            return False
        owner = db.scalar(
            select(ClientPortfolioOwnership).where(
                ClientPortfolioOwnership.client_id == resource_id,
                ClientPortfolioOwnership.status == "ACTIVE",
            )
        )
        if owner is None:
            return False
        return (user.role == "PARTNER" and owner.partner_user_id == user.id) or (
            user.role == "MANAGER" and owner.manager_user_id == user.id
        )
    if resource_type == "ENGAGEMENT":
        engagement = db.get(Engagement, resource_id)
        if engagement is None or engagement.is_archived:
            return False
        if engagement.partner_user_id == user.id or engagement.manager_user_id == user.id:
            return True
        team_match = db.scalar(
            select(EngagementTeamMember.id)
            .join(StaffProfile, StaffProfile.id == EngagementTeamMember.staff_id)
            .where(
                EngagementTeamMember.engagement_id == resource_id,
                EngagementTeamMember.status == "ACTIVE",
                StaffProfile.auth_user_id == user.id,
                StaffProfile.is_archived.is_(False),
            )
            .limit(1)
        )
        return team_match is not None
    return False


def _validate_resource(db: Session, user: AuthUser, resource_type: str, resource_id: str) -> str:
    normalized = resource_type.strip().upper()
    if normalized not in _ALLOWED_RESOURCE_TYPES:
        raise ApiError("INVALID_DOCUMENT_RESOURCE", "resource_type must be CLIENT or ENGAGEMENT", 422)
    if not _can_access_resource(db, user, normalized, resource_id):
        raise ApiError("DOCUMENT_RESOURCE_ACCESS_DENIED", "You do not have access to the linked resource", 403)
    return normalized


def _accessible_document(db: Session, user: AuthUser, document_id: str, permission: Permission) -> Document:
    _require(user, permission)
    document = db.get(Document, document_id)
    if document is None or document.is_archived:
        raise ApiError("DOCUMENT_NOT_FOUND", "Document not found", 404)
    if not _can_access_resource(db, user, document.resource_type, document.resource_id):
        raise ApiError("DOCUMENT_ACCESS_DENIED", "You do not have access to this document", 403)
    return document


def _log_access(db: Session, request: Request, user: AuthUser, document: Document, action: str, version: DocumentVersion | None = None) -> None:
    db.add(
        DocumentAccessLog(
            document_id=document.id,
            document_version_id=version.id if version else None,
            actor_user_id=user.id,
            action=action,
            outcome="SUCCESS",
            correlation_id=correlation_id_from_request(request),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )


def _business_event(db: Session, request: Request, user: AuthUser, document: Document, event_type: str, summary: str, detail: dict[str, object]) -> None:
    payload = json.dumps(detail, default=str)
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="DOCUMENT", resource_id=document.id, summary=summary, detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="DOCUMENT", resource_id=document.id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


def _detail(db: Session, document: Document) -> DocumentDetail:
    versions = list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
        )
    )
    return DocumentDetail(
        **DocumentView.model_validate(document).model_dump(),
        versions=[DocumentVersionView.model_validate(item) for item in versions],
    )


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    resource_type: str = Form(...),
    resource_id: str = Form(...),
    title: str = Form(...),
    document_type: str = Form("GENERAL"),
    confidentiality_level: str = Form("INTERNAL"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> DocumentDetail:
    _require(user, Permission.DOCUMENT_UPLOAD)
    normalized_resource = _validate_resource(db, user, resource_type, resource_id)
    content = await file.read(_MAX_FILE_BYTES + 1)
    if not content:
        raise ApiError("EMPTY_DOCUMENT", "Uploaded document is empty", 422)
    if len(content) > _MAX_FILE_BYTES:
        raise ApiError("DOCUMENT_TOO_LARGE", "Document exceeds the 25 MB upload limit", 413)
    filename = (file.filename or "document.bin").strip()[:255]
    document = Document(
        document_code=f"FRC-DOC-{uuid.uuid4().hex[:12].upper()}",
        resource_type=normalized_resource,
        resource_id=resource_id,
        title=title.strip(),
        document_type=document_type.strip().upper(),
        confidentiality_level=confidentiality_level.strip().upper(),
        created_by_user_id=user.id,
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        original_filename=filename,
        content_type=(file.content_type or "application/octet-stream")[:150],
        size_bytes=len(content),
        sha256_hex=hashlib.sha256(content).hexdigest(),
        content_bytes=content,
        change_note="Initial version",
        uploaded_by_user_id=user.id,
    )
    db.add(version)
    db.flush()
    _log_access(db, request, user, document, "UPLOAD", version)
    _business_event(db, request, user, document, "DOCUMENT_UPLOADED", f"Document {document.document_code} uploaded", {"version": 1, "filename": filename})
    db.commit()
    db.refresh(document)
    return _detail(db, document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    resource_type: str | None = None,
    resource_id: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> DocumentListResponse:
    _require(user, Permission.DOCUMENT_VIEW)
    stmt = select(Document).where(Document.is_archived.is_(False))
    if resource_type:
        stmt = stmt.where(Document.resource_type == resource_type.strip().upper())
    if resource_id:
        stmt = stmt.where(Document.resource_id == resource_id)
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Document.title.ilike(needle), Document.document_code.ilike(needle), Document.document_type.ilike(needle)))
    rows = list(db.scalars(stmt.order_by(Document.updated_at.desc()).limit(500)))
    accessible = [row for row in rows if _can_access_resource(db, user, row.resource_type, row.resource_id)]
    total = len(accessible)
    start = (page - 1) * page_size
    items = accessible[start : start + page_size]
    return DocumentListResponse(items=[DocumentView.model_validate(item) for item in items], page=page, page_size=page_size, total=total)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> DocumentDetail:
    document = _accessible_document(db, user, document_id, Permission.DOCUMENT_VIEW)
    _log_access(db, request, user, document, "VIEW")
    db.commit()
    return _detail(db, document)


@router.post("/{document_id}/versions", response_model=DocumentDetail)
async def upload_new_version(
    document_id: str,
    request: Request,
    expected_version: int = Form(...),
    change_note: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> DocumentDetail:
    document = _accessible_document(db, user, document_id, Permission.DOCUMENT_VERSION)
    if document.current_version != expected_version:
        raise ApiError("VERSION_CONFLICT", "Document has changed; reload before uploading a new version", 409, {"current_version": document.current_version})
    content = await file.read(_MAX_FILE_BYTES + 1)
    if not content:
        raise ApiError("EMPTY_DOCUMENT", "Uploaded document is empty", 422)
    if len(content) > _MAX_FILE_BYTES:
        raise ApiError("DOCUMENT_TOO_LARGE", "Document exceeds the 25 MB upload limit", 413)
    next_version = document.current_version + 1
    version = DocumentVersion(
        document_id=document.id,
        version_number=next_version,
        original_filename=(file.filename or "document.bin").strip()[:255],
        content_type=(file.content_type or "application/octet-stream")[:150],
        size_bytes=len(content),
        sha256_hex=hashlib.sha256(content).hexdigest(),
        content_bytes=content,
        change_note=(change_note or "").strip() or None,
        uploaded_by_user_id=user.id,
    )
    document.current_version = next_version
    db.add(version)
    db.flush()
    _log_access(db, request, user, document, "VERSION_UPLOAD", version)
    _business_event(db, request, user, document, "DOCUMENT_VERSION_ADDED", f"Version {next_version} added to {document.document_code}", {"version": next_version})
    db.commit()
    db.refresh(document)
    return _detail(db, document)


@router.get("/{document_id}/versions/{version_number}/download")
def download_document_version(
    document_id: str,
    version_number: int,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> Response:
    document = _accessible_document(db, user, document_id, Permission.DOCUMENT_VIEW)
    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_number == version_number,
        )
    )
    if version is None:
        raise ApiError("DOCUMENT_VERSION_NOT_FOUND", "Document version not found", 404)
    _log_access(db, request, user, document, "DOWNLOAD", version)
    db.commit()
    safe_filename = quote(version.original_filename)
    return Response(
        content=version.content_bytes,
        media_type=version.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "X-Content-SHA256": version.sha256_hex,
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/{document_id}/archive", response_model=DocumentView)
def archive_document(
    document_id: str,
    request: Request,
    expected_version: int = Form(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> DocumentView:
    document = _accessible_document(db, user, document_id, Permission.DOCUMENT_ARCHIVE)
    if document.current_version != expected_version:
        raise ApiError("VERSION_CONFLICT", "Document has changed; reload before archiving", 409, {"current_version": document.current_version})
    document.is_archived = True
    document.archived_at = _utcnow()
    document.archived_by_user_id = user.id
    _log_access(db, request, user, document, "ARCHIVE")
    _business_event(db, request, user, document, "DOCUMENT_ARCHIVED", f"Document {document.document_code} archived", {"version": document.current_version})
    db.commit()
    db.refresh(document)
    return DocumentView.model_validate(document)


@router.get("/{document_id}/access-log", response_model=list[DocumentAccessLogView])
def document_access_log(
    document_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> list[DocumentAccessLogView]:
    document = _accessible_document(db, user, document_id, Permission.DOCUMENT_VIEW)
    rows = list(
        db.scalars(
            select(DocumentAccessLog)
            .where(DocumentAccessLog.document_id == document.id)
            .order_by(DocumentAccessLog.created_at.desc())
            .limit(200)
        )
    )
    return [DocumentAccessLogView.model_validate(row) for row in rows]
