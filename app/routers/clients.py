from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.client_lifecycle_models import ClientArchiveEvent, ClientPortfolioOwnership
from app.client_models import Client, ClientAddress, ClientContact, ClientIdentifier, ClientStatusHistory
from app.client_schemas import (
    ClientActivityView,
    ClientAddressView,
    ClientArchiveRequest,
    ClientContactView,
    ClientCreateRequest,
    ClientDetail,
    ClientIdentifierView,
    ClientListResponse,
    ClientSummary,
    ClientUpdateRequest,
)
from app.clients.lifecycle import DuplicateCandidate, find_duplicate_warnings, validate_transition
from app.db import get_db
from app.deps import require_password_changed
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def _require_permission(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _ownership(db: Session, client_id: str) -> ClientPortfolioOwnership | None:
    return db.scalar(
        select(ClientPortfolioOwnership).where(
            ClientPortfolioOwnership.client_id == client_id,
            ClientPortfolioOwnership.status == "ACTIVE",
        )
    )


def _can_access_client(db: Session, user: AuthUser, client: Client) -> bool:
    if user.role == "SUPER_ADMIN":
        return True
    owner = _ownership(db, client.id)
    if owner is None:
        return False
    if user.role == "PARTNER" and owner.partner_user_id == user.id:
        return True
    if user.role == "MANAGER" and owner.manager_user_id == user.id:
        return True
    return False


def _get_accessible_client(db: Session, user: AuthUser, client_id: str, permission: Permission) -> Client:
    _require_permission(user, permission)
    client = db.get(Client, client_id)
    if client is None:
        raise ApiError("CLIENT_NOT_FOUND", "Client not found", 404)
    if not _can_access_client(db, user, client):
        raise ApiError("CLIENT_ACCESS_DENIED", "You do not have access to this client", 403)
    return client


def _validate_owner_users(db: Session, partner_user_id: str, manager_user_id: str | None) -> None:
    partner = db.get(AuthUser, partner_user_id)
    if partner is None or partner.status != "ACTIVE" or partner.role not in {"PARTNER", "SUPER_ADMIN"}:
        raise ApiError("INVALID_PARTNER", "partner_user_id must reference an active Partner/Super Admin", 422)
    if manager_user_id:
        manager = db.get(AuthUser, manager_user_id)
        if manager is None or manager.status != "ACTIVE" or manager.role != "MANAGER":
            raise ApiError("INVALID_MANAGER", "manager_user_id must reference an active Manager", 422)


def _new_client_code() -> str:
    # Collision-resistant immutable external code; a formal configurable naming series can replace this later.
    return f"FRC-CLI-{uuid.uuid4().hex[:10].upper()}"


def _serialize_detail(db: Session, client: Client) -> ClientDetail:
    contacts = list(db.scalars(select(ClientContact).where(ClientContact.client_id == client.id).order_by(ClientContact.created_at)))
    addresses = list(db.scalars(select(ClientAddress).where(ClientAddress.client_id == client.id).order_by(ClientAddress.created_at)))
    identifiers = list(db.scalars(select(ClientIdentifier).where(ClientIdentifier.client_id == client.id).order_by(ClientIdentifier.identifier_type)))
    base = ClientSummary.model_validate(client).model_dump()
    return ClientDetail(
        **base,
        contacts=[ClientContactView.model_validate(item) for item in contacts],
        addresses=[ClientAddressView.model_validate(item) for item in addresses],
        identifiers=[ClientIdentifierView.model_validate(item) for item in identifiers],
    )


def _record_events(
    db: Session,
    *,
    request: Request,
    user: AuthUser,
    client: Client,
    event_type: str,
    summary: str,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
) -> None:
    correlation_id = correlation_id_from_request(request)
    db.add(
        ActivityEvent(
            actor_user_id=user.id,
            event_type=event_type,
            resource_type="CLIENT",
            resource_id=client.id,
            summary=summary,
            detail_json=json.dumps(after or {}, default=str),
        )
    )
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            event_type=event_type,
            resource_type="CLIENT",
            resource_id=client.id,
            correlation_id=correlation_id,
            outcome="SUCCESS",
            before_json=json.dumps(before, default=str) if before is not None else None,
            after_json=json.dumps(after, default=str) if after is not None else None,
        )
    )


@router.post("", response_model=ClientDetail, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> ClientDetail:
    _require_permission(user, Permission.CLIENT_CREATE)
    _validate_owner_users(db, payload.partner_user_id, payload.manager_user_id)

    candidates = list(db.scalars(select(Client).where(Client.is_archived.is_(False)).limit(500)))
    warnings = find_duplicate_warnings(
        legal_name=payload.legal_name,
        trading_name=payload.trading_name,
        candidates=[DuplicateCandidate(item.id, item.legal_name, item.trading_name) for item in candidates],
    )

    client = Client(
        client_code=_new_client_code(),
        legal_name=payload.legal_name.strip(),
        trading_name=payload.trading_name.strip() if payload.trading_name else None,
        entity_type=payload.entity_type,
        industry=payload.industry,
        client_group=payload.client_group,
        confidentiality_level=payload.confidentiality_level,
        status="PROSPECT",
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(client)
    db.flush()

    for item in payload.contacts:
        db.add(ClientContact(client_id=client.id, **item.model_dump()))
    for item in payload.addresses:
        db.add(ClientAddress(client_id=client.id, **item.model_dump()))
    for item in payload.identifiers:
        db.add(
            ClientIdentifier(
                client_id=client.id,
                identifier_type=item.identifier_type,
                value=item.value.strip(),
                normalized_value=_normalize_identifier(item.value),
                issued_by=item.issued_by,
            )
        )

    db.add(
        ClientPortfolioOwnership(
            client_id=client.id,
            partner_user_id=payload.partner_user_id,
            manager_user_id=payload.manager_user_id,
            assigned_by_user_id=user.id,
        )
    )
    db.add(
        ClientStatusHistory(
            client_id=client.id,
            from_status=None,
            to_status="PROSPECT",
            reason="Client created",
            changed_by_user_id=user.id,
            correlation_id=correlation_id_from_request(request),
        )
    )
    _record_events(
        db,
        request=request,
        user=user,
        client=client,
        event_type="CLIENT_CREATED",
        summary=f"Client {client.client_code} created",
        after={"legal_name": client.legal_name, "duplicate_warnings": [warning.__dict__ for warning in warnings]},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("CLIENT_DUPLICATE_IDENTIFIER", "Client code or identifier already exists", 409) from exc
    db.refresh(client)
    return _serialize_detail(db, client)


@router.get("", response_model=ClientListResponse)
def list_clients(
    q: str | None = Query(default=None, max_length=200),
    client_status: str | None = Query(default=None, alias="status", max_length=30),
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> ClientListResponse:
    _require_permission(user, Permission.CLIENT_VIEW)
    stmt = select(Client)
    if not include_archived:
        stmt = stmt.where(Client.is_archived.is_(False))
    if client_status:
        stmt = stmt.where(Client.status == client_status.strip().upper())
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Client.legal_name.ilike(needle), Client.trading_name.ilike(needle), Client.client_code.ilike(needle)))

    if user.role != "SUPER_ADMIN":
        stmt = stmt.join(ClientPortfolioOwnership, ClientPortfolioOwnership.client_id == Client.id).where(
            ClientPortfolioOwnership.status == "ACTIVE"
        )
        if user.role == "PARTNER":
            stmt = stmt.where(ClientPortfolioOwnership.partner_user_id == user.id)
        elif user.role == "MANAGER":
            stmt = stmt.where(ClientPortfolioOwnership.manager_user_id == user.id)
        else:
            return ClientListResponse(items=[], page=page, page_size=page_size, total=0)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)
    clients = list(db.scalars(stmt.order_by(Client.legal_name, Client.client_code).offset((page - 1) * page_size).limit(page_size)))
    return ClientListResponse(items=[ClientSummary.model_validate(item) for item in clients], page=page, page_size=page_size, total=total)


@router.get("/export")
def export_clients(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> StreamingResponse:
    _require_permission(user, Permission.CLIENT_EXPORT)
    stmt = select(Client).where(Client.is_archived.is_(False))
    if user.role != "SUPER_ADMIN":
        stmt = stmt.join(ClientPortfolioOwnership, ClientPortfolioOwnership.client_id == Client.id).where(
            ClientPortfolioOwnership.status == "ACTIVE"
        )
        if user.role == "PARTNER":
            stmt = stmt.where(ClientPortfolioOwnership.partner_user_id == user.id)
        elif user.role == "MANAGER":
            stmt = stmt.where(ClientPortfolioOwnership.manager_user_id == user.id)
        else:
            stmt = stmt.where(False)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["client_code", "legal_name", "trading_name", "entity_type", "industry", "status"])
    for client in db.scalars(stmt.order_by(Client.client_code)):
        writer.writerow([client.client_code, client.legal_name, client.trading_name or "", client.entity_type, client.industry or "", client.status])
    payload = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=clients.csv"},
    )


@router.get("/{client_id}", response_model=ClientDetail)
def get_client(
    client_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> ClientDetail:
    client = _get_accessible_client(db, user, client_id, Permission.CLIENT_VIEW)
    return _serialize_detail(db, client)


@router.patch("/{client_id}", response_model=ClientDetail)
def update_client(
    client_id: str,
    payload: ClientUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> ClientDetail:
    client = _get_accessible_client(db, user, client_id, Permission.CLIENT_UPDATE)
    if client.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Client record has changed; reload before updating", 409, {"current_version": client.version})
    if client.is_archived:
        raise ApiError("CLIENT_ARCHIVED", "Archived clients cannot be edited", 409)

    before = ClientSummary.model_validate(client).model_dump(mode="json")
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    for field, value in updates.items():
        if field in {"entity_type", "confidentiality_level"} and isinstance(value, str):
            value = value.strip().upper()
        if isinstance(value, str):
            value = value.strip()
        setattr(client, field, value)
    client.version += 1
    client.updated_by_user_id = user.id
    client.updated_at = _utcnow()
    after = ClientSummary.model_validate(client).model_dump(mode="json")
    _record_events(db, request=request, user=user, client=client, event_type="CLIENT_UPDATED", summary=f"Client {client.client_code} updated", before=before, after=after)
    db.commit()
    db.refresh(client)
    return _serialize_detail(db, client)


@router.post("/{client_id}/archive", response_model=ClientDetail)
def archive_client(
    client_id: str,
    payload: ClientArchiveRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> ClientDetail:
    client = _get_accessible_client(db, user, client_id, Permission.CLIENT_ARCHIVE)
    if client.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Client record has changed; reload before archiving", 409, {"current_version": client.version})
    if client.is_archived:
        raise ApiError("CLIENT_ALREADY_ARCHIVED", "Client is already archived", 409)

    decision = validate_transition(client.status, "ARCHIVED")
    if not decision.allowed:
        raise ApiError(decision.reason, "Current lifecycle state cannot be archived directly", 409, {"status": client.status})

    before_status = client.status
    before = ClientSummary.model_validate(client).model_dump(mode="json")
    client.status = "ARCHIVED"
    client.is_archived = True
    client.archived_at = _utcnow()
    client.archived_by_user_id = user.id
    client.updated_by_user_id = user.id
    client.version += 1
    db.add(
        ClientArchiveEvent(
            client_id=client.id,
            action="ARCHIVE",
            prior_status=before_status,
            resulting_status="ARCHIVED",
            reason=payload.reason,
            actor_user_id=user.id,
            correlation_id=correlation_id_from_request(request),
        )
    )
    db.add(
        ClientStatusHistory(
            client_id=client.id,
            from_status=before_status,
            to_status="ARCHIVED",
            reason=payload.reason,
            changed_by_user_id=user.id,
            correlation_id=correlation_id_from_request(request),
        )
    )
    after = ClientSummary.model_validate(client).model_dump(mode="json")
    _record_events(db, request=request, user=user, client=client, event_type="CLIENT_ARCHIVED", summary=f"Client {client.client_code} archived", before=before, after=after)
    db.commit()
    db.refresh(client)
    return _serialize_detail(db, client)


@router.get("/{client_id}/activity", response_model=list[ClientActivityView])
def client_activity(
    client_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> list[ClientActivityView]:
    client = _get_accessible_client(db, user, client_id, Permission.CLIENT_VIEW)
    items = list(
        db.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.resource_type == "CLIENT", ActivityEvent.resource_id == client.id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit)
        )
    )
    return [ClientActivityView.model_validate(item) for item in items]
