from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.client_models import Client
from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement, EngagementNumberSequence, EngagementTeamMember
from app.engagement_schemas import (
    EngagementCreateRequest,
    EngagementDetail,
    EngagementListResponse,
    EngagementTeamAssignRequest,
    EngagementTeamMemberView,
    EngagementUpdateRequest,
    EngagementView,
)
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile

router = APIRouter(prefix="/api/v1/engagements", tags=["engagements"])

_ALLOWED_TEAM_ROLES = {"PARTNER", "MANAGER", "REVIEWER", "SENIOR", "TEAM_MEMBER", "STUDENT"}
_ALLOWED_CLIENT_STATES = {"APPROVED", "ONBOARDING", "ACTIVE"}


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _validate_lead_users(db: Session, partner_user_id: str, manager_user_id: str | None) -> None:
    partner = db.get(AuthUser, partner_user_id)
    if partner is None or partner.status != "ACTIVE" or partner.role not in {"PARTNER", "SUPER_ADMIN"}:
        raise ApiError("INVALID_PARTNER", "partner_user_id must reference an active Partner/Super Admin", 422)
    if manager_user_id:
        manager = db.get(AuthUser, manager_user_id)
        if manager is None or manager.status != "ACTIVE" or manager.role != "MANAGER":
            raise ApiError("INVALID_MANAGER", "manager_user_id must reference an active Manager", 422)


def _next_engagement_code(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    sequence = db.scalar(
        select(EngagementNumberSequence)
        .where(EngagementNumberSequence.year == year)
        .with_for_update()
    )
    if sequence is None:
        sequence = EngagementNumberSequence(year=year, next_number=2)
        db.add(sequence)
        number = 1
    else:
        number = sequence.next_number
        sequence.next_number += 1
    return f"FRC-ENG-{year}-{number:06d}"


def _accessible_stmt(user: AuthUser):
    stmt = select(Engagement).where(Engagement.is_archived.is_(False))
    if user.role == "SUPER_ADMIN":
        return stmt
    team_engagements = (
        select(EngagementTeamMember.engagement_id)
        .join(StaffProfile, StaffProfile.id == EngagementTeamMember.staff_id)
        .where(
            StaffProfile.auth_user_id == user.id,
            EngagementTeamMember.status == "ACTIVE",
        )
    )
    return stmt.where(
        or_(
            Engagement.partner_user_id == user.id,
            Engagement.manager_user_id == user.id,
            Engagement.id.in_(team_engagements),
        )
    )


def _accessible_engagement(db: Session, user: AuthUser, engagement_id: str, permission: Permission) -> Engagement:
    _require(user, permission)
    engagement = db.get(Engagement, engagement_id)
    if engagement is None or engagement.is_archived:
        raise ApiError("ENGAGEMENT_NOT_FOUND", "Engagement not found", 404)
    if user.role == "SUPER_ADMIN":
        return engagement
    allowed = db.scalar(_accessible_stmt(user).where(Engagement.id == engagement_id))
    if allowed is None:
        raise ApiError("ENGAGEMENT_ACCESS_DENIED", "You do not have access to this engagement", 403)
    return engagement


def _detail(db: Session, engagement: Engagement) -> EngagementDetail:
    team = list(
        db.scalars(
            select(EngagementTeamMember)
            .where(EngagementTeamMember.engagement_id == engagement.id)
            .order_by(EngagementTeamMember.assignment_role, EngagementTeamMember.created_at)
        )
    )
    return EngagementDetail(
        **EngagementView.model_validate(engagement).model_dump(),
        team=[EngagementTeamMemberView.model_validate(item) for item in team],
    )


def _event(
    db: Session,
    request: Request,
    user: AuthUser,
    engagement: Engagement,
    event_type: str,
    summary: str,
    detail: dict[str, object] | None = None,
) -> None:
    correlation_id = correlation_id_from_request(request)
    db.add(
        ActivityEvent(
            actor_user_id=user.id,
            event_type=event_type,
            resource_type="ENGAGEMENT",
            resource_id=engagement.id,
            summary=summary,
            detail_json=json.dumps(detail or {}, default=str),
        )
    )
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            event_type=event_type,
            resource_type="ENGAGEMENT",
            resource_id=engagement.id,
            correlation_id=correlation_id,
            outcome="SUCCESS",
            detail_json=json.dumps(detail or {}, default=str),
        )
    )


@router.post("", response_model=EngagementDetail, status_code=status.HTTP_201_CREATED)
def create_engagement(
    payload: EngagementCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementDetail:
    _require(user, Permission.ENGAGEMENT_CREATE)
    client = db.get(Client, payload.client_id)
    if client is None or client.is_archived:
        raise ApiError("CLIENT_NOT_FOUND", "Client not found", 404)
    if client.status not in _ALLOWED_CLIENT_STATES:
        raise ApiError(
            "CLIENT_NOT_READY_FOR_ENGAGEMENT",
            "Client must be approved, onboarding, or active before engagement creation",
            409,
            {"client_status": client.status},
        )
    _validate_lead_users(db, payload.partner_user_id, payload.manager_user_id)

    engagement = Engagement(
        engagement_code=_next_engagement_code(db),
        client_id=payload.client_id,
        service_type=payload.service_type,
        title=payload.title.strip(),
        period_start=payload.period_start,
        period_end=payload.period_end,
        partner_user_id=payload.partner_user_id,
        manager_user_id=payload.manager_user_id,
        priority=payload.priority,
        deadline=payload.deadline,
        fee_currency=payload.fee_currency,
        agreed_fee_minor=payload.agreed_fee_minor,
        budget_minutes=payload.budget_minutes,
        confidentiality_level=payload.confidentiality_level,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(engagement)
    db.flush()
    _event(db, request, user, engagement, "ENGAGEMENT_CREATED", f"Engagement {engagement.engagement_code} created")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("ENGAGEMENT_CONFLICT", "Engagement could not be created due to a data conflict", 409) from exc
    db.refresh(engagement)
    return _detail(db, engagement)


@router.get("", response_model=EngagementListResponse)
def list_engagements(
    q: str | None = Query(default=None, max_length=200),
    client_id: str | None = None,
    service_type: str | None = None,
    engagement_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementListResponse:
    _require(user, Permission.ENGAGEMENT_VIEW)
    stmt = _accessible_stmt(user)
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(Engagement.title.ilike(needle), Engagement.engagement_code.ilike(needle)))
    if client_id:
        stmt = stmt.where(Engagement.client_id == client_id)
    if service_type:
        stmt = stmt.where(Engagement.service_type == service_type.strip().upper())
    if engagement_status:
        stmt = stmt.where(Engagement.status == engagement_status.strip().upper())
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(Engagement.deadline.is_(None), Engagement.deadline, Engagement.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return EngagementListResponse(
        items=[EngagementView.model_validate(item) for item in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{engagement_id}", response_model=EngagementDetail)
def get_engagement(
    engagement_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementDetail:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_VIEW)
    return _detail(db, engagement)


@router.patch("/{engagement_id}", response_model=EngagementDetail)
def update_engagement(
    engagement_id: str,
    payload: EngagementUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementDetail:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_ASSIGN)
    if engagement.version != payload.expected_version:
        raise ApiError(
            "VERSION_CONFLICT",
            "Engagement record has changed; reload before updating",
            409,
            {"current_version": engagement.version},
        )
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    partner_id = updates.get("partner_user_id", engagement.partner_user_id)
    manager_id = updates.get("manager_user_id", engagement.manager_user_id)
    _validate_lead_users(db, partner_id, manager_id)
    start = updates.get("period_start", engagement.period_start)
    end = updates.get("period_end", engagement.period_end)
    if start and end and end < start:
        raise ApiError("INVALID_ENGAGEMENT_PERIOD", "period_end must be on or after period_start", 422)
    for key, value in updates.items():
        if key in {"service_type", "priority", "fee_currency", "confidentiality_level"} and isinstance(value, str):
            value = value.strip().upper()
        if key == "title" and isinstance(value, str):
            value = value.strip()
        setattr(engagement, key, value)
    engagement.version += 1
    engagement.updated_by_user_id = user.id
    _event(db, request, user, engagement, "ENGAGEMENT_UPDATED", f"Engagement {engagement.engagement_code} updated", updates)
    db.commit()
    db.refresh(engagement)
    return _detail(db, engagement)


@router.post("/{engagement_id}/team", response_model=EngagementTeamMemberView, status_code=status.HTTP_201_CREATED)
def assign_team_member(
    engagement_id: str,
    payload: EngagementTeamAssignRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementTeamMemberView:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_ASSIGN)
    if payload.assignment_role not in _ALLOWED_TEAM_ROLES:
        raise ApiError("INVALID_ASSIGNMENT_ROLE", "Unsupported engagement assignment role", 422)
    staff = db.get(StaffProfile, payload.staff_id)
    if staff is None or staff.is_archived or staff.employment_status != "ACTIVE":
        raise ApiError("STAFF_NOT_AVAILABLE", "Staff member is not active/available for assignment", 422)
    member = db.scalar(
        select(EngagementTeamMember).where(
            EngagementTeamMember.engagement_id == engagement.id,
            EngagementTeamMember.staff_id == payload.staff_id,
        )
    )
    if member is None:
        member = EngagementTeamMember(
            engagement_id=engagement.id,
            staff_id=payload.staff_id,
            assignment_role=payload.assignment_role,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            assigned_by_user_id=user.id,
        )
        db.add(member)
    else:
        member.assignment_role = payload.assignment_role
        member.starts_on = payload.starts_on
        member.ends_on = payload.ends_on
        member.status = "ACTIVE"
        member.assigned_by_user_id = user.id
    _event(
        db,
        request,
        user,
        engagement,
        "ENGAGEMENT_TEAM_ASSIGNED",
        f"Staff {staff.staff_code} assigned to {engagement.engagement_code}",
        {"staff_id": staff.id, "assignment_role": payload.assignment_role},
    )
    db.commit()
    db.refresh(member)
    return EngagementTeamMemberView.model_validate(member)
