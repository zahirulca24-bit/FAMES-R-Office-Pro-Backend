from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.engagement_closure_models import EngagementReviewAction
from app.engagement_closure_schemas import (
    EngagementBlockers,
    EngagementCloseRequest,
    EngagementReopenRequest,
    EngagementReviewActionView,
    EngagementTransitionRequest,
    EngagementWorkflowView,
)
from app.engagement_models import Engagement
from app.engagement_template_models import EngagementGeneratedTask, EngagementRequiredDocument
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.routers.engagements import _accessible_engagement, _accessible_stmt
from app.workflow_models import RecordLock

router = APIRouter(prefix="/api/v1/engagement-workflow", tags=["engagement-workflow"])


def _blockers(db: Session, engagement_id: str) -> EngagementBlockers:
    incomplete = int(
        db.scalar(
            select(func.count()).select_from(EngagementGeneratedTask).where(
                EngagementGeneratedTask.engagement_id == engagement_id,
                EngagementGeneratedTask.required.is_(True),
                EngagementGeneratedTask.status != "COMPLETED",
            )
        )
        or 0
    )
    overdue = int(
        db.scalar(
            select(func.count()).select_from(EngagementGeneratedTask).where(
                EngagementGeneratedTask.engagement_id == engagement_id,
                EngagementGeneratedTask.required.is_(True),
                EngagementGeneratedTask.status != "COMPLETED",
                EngagementGeneratedTask.escalation_state == "OVERDUE",
            )
        )
        or 0
    )
    pending_docs = int(
        db.scalar(
            select(func.count()).select_from(EngagementRequiredDocument).where(
                EngagementRequiredDocument.engagement_id == engagement_id,
                EngagementRequiredDocument.required.is_(True),
                EngagementRequiredDocument.status.notin_(["RECEIVED", "ACCEPTED", "COMPLETE", "WAIVED"]),
            )
        )
        or 0
    )
    messages: list[str] = []
    if incomplete:
        messages.append(f"{incomplete} required task(s) incomplete")
    if overdue:
        messages.append(f"{overdue} required task(s) overdue")
    if pending_docs:
        messages.append(f"{pending_docs} required document(s) pending")
    return EngagementBlockers(
        incomplete_required_tasks=incomplete,
        overdue_required_tasks=overdue,
        pending_required_documents=pending_docs,
        blockers=messages,
    )


def _lock(db: Session, engagement_id: str) -> RecordLock:
    lock = db.scalar(
        select(RecordLock).where(
            RecordLock.resource_type == "ENGAGEMENT",
            RecordLock.resource_id == engagement_id,
        )
    )
    if lock is None:
        lock = RecordLock(resource_type="ENGAGEMENT", resource_id=engagement_id, state="OPEN", revision_number=1)
        db.add(lock)
        db.flush()
    return lock


def _view(db: Session, engagement: Engagement) -> EngagementWorkflowView:
    lock = _lock(db, engagement.id)
    return EngagementWorkflowView(
        engagement_id=engagement.id,
        engagement_code=engagement.engagement_code,
        status=engagement.status,
        version=engagement.version,
        lock_state=lock.state,
        revision_number=lock.revision_number,
        blockers=_blockers(db, engagement.id),
    )


def _record(
    db: Session,
    request: Request,
    user: AuthUser,
    engagement: Engagement,
    action_type: str,
    from_status: str,
    to_status: str,
    reason: str | None,
    blockers: EngagementBlockers,
    revision_number: int,
) -> None:
    cid = correlation_id_from_request(request)
    snapshot = json.dumps(blockers.model_dump())
    db.add(
        EngagementReviewAction(
            engagement_id=engagement.id,
            action_type=action_type,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            blocker_snapshot_json=snapshot,
            actor_user_id=user.id,
            correlation_id=cid,
            revision_number=revision_number,
        )
    )
    db.add(
        ActivityEvent(
            actor_user_id=user.id,
            event_type=action_type,
            resource_type="ENGAGEMENT",
            resource_id=engagement.id,
            summary=f"Engagement {engagement.engagement_code}: {from_status} → {to_status}",
            detail_json=snapshot,
        )
    )
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            event_type=action_type,
            resource_type="ENGAGEMENT",
            resource_id=engagement.id,
            correlation_id=cid,
            outcome="SUCCESS",
            detail_json=snapshot,
        )
    )


def _version_check(engagement: Engagement, expected_version: int) -> None:
    if engagement.version != expected_version:
        raise ApiError(
            "VERSION_CONFLICT",
            "Engagement record has changed; reload before workflow action",
            409,
            {"current_version": engagement.version},
        )


@router.get("/review-queue", response_model=list[EngagementWorkflowView])
def review_queue(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> list[EngagementWorkflowView]:
    rows = list(
        db.scalars(
            _accessible_stmt(user)
            .where(Engagement.status.in_(["UNDER_REVIEW", "READY_TO_CLOSE"]))
            .order_by(Engagement.deadline.is_(None), Engagement.deadline, Engagement.updated_at)
            .limit(limit)
        )
    )
    return [_view(db, item) for item in rows]


@router.get("/{engagement_id}", response_model=EngagementWorkflowView)
def workflow_status(
    engagement_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementWorkflowView:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_VIEW)
    return _view(db, engagement)


@router.post("/{engagement_id}/submit-review", response_model=EngagementWorkflowView)
def submit_review(
    engagement_id: str,
    payload: EngagementTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementWorkflowView:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_ASSIGN)
    _version_check(engagement, payload.expected_version)
    if engagement.status not in {"DRAFT", "IN_PROGRESS", "REOPENED"}:
        raise ApiError("INVALID_ENGAGEMENT_STATE", "Engagement cannot be submitted for review from its current state", 409)
    blockers = _blockers(db, engagement.id)
    if blockers.blockers:
        raise ApiError("ENGAGEMENT_COMPLETION_BLOCKED", "Engagement has unresolved completion blockers", 409, blockers.model_dump())
    lock = _lock(db, engagement.id)
    old = engagement.status
    engagement.status = "UNDER_REVIEW"
    engagement.version += 1
    _record(db, request, user, engagement, "ENGAGEMENT_SUBMITTED_FOR_REVIEW", old, engagement.status, payload.reason, blockers, lock.revision_number)
    db.commit()
    return _view(db, engagement)


@router.post("/{engagement_id}/approve", response_model=EngagementWorkflowView)
def approve_review(
    engagement_id: str,
    payload: EngagementTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementWorkflowView:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_APPROVE)
    _version_check(engagement, payload.expected_version)
    if engagement.status != "UNDER_REVIEW":
        raise ApiError("INVALID_ENGAGEMENT_STATE", "Only an engagement under review can be approved", 409)
    blockers = _blockers(db, engagement.id)
    if blockers.blockers:
        raise ApiError("ENGAGEMENT_COMPLETION_BLOCKED", "Engagement has unresolved completion blockers", 409, blockers.model_dump())
    lock = _lock(db, engagement.id)
    old = engagement.status
    engagement.status = "READY_TO_CLOSE"
    engagement.version += 1
    _record(db, request, user, engagement, "ENGAGEMENT_REVIEW_APPROVED", old, engagement.status, payload.reason, blockers, lock.revision_number)
    db.commit()
    return _view(db, engagement)


@router.post("/{engagement_id}/close", response_model=EngagementWorkflowView)
def close_engagement(
    engagement_id: str,
    payload: EngagementCloseRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementWorkflowView:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_CLOSE)
    _version_check(engagement, payload.expected_version)
    if engagement.status != "READY_TO_CLOSE":
        raise ApiError("INVALID_ENGAGEMENT_STATE", "Engagement must be approved and ready to close", 409)
    blockers = _blockers(db, engagement.id)
    if blockers.blockers:
        raise ApiError("ENGAGEMENT_COMPLETION_BLOCKED", "Engagement has unresolved completion blockers", 409, blockers.model_dump())
    lock = _lock(db, engagement.id)
    old = engagement.status
    engagement.status = "CLOSED"
    engagement.version += 1
    lock.state = "LOCKED"
    lock.locked_by_user_id = user.id
    lock.locked_at = datetime.now(timezone.utc)
    _record(db, request, user, engagement, "ENGAGEMENT_CLOSED", old, engagement.status, payload.reason, blockers, lock.revision_number)
    db.commit()
    return _view(db, engagement)


@router.post("/{engagement_id}/reopen", response_model=EngagementWorkflowView)
def reopen_engagement(
    engagement_id: str,
    payload: EngagementReopenRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> EngagementWorkflowView:
    engagement = _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_REOPEN)
    _version_check(engagement, payload.expected_version)
    if engagement.status != "CLOSED":
        raise ApiError("INVALID_ENGAGEMENT_STATE", "Only a closed engagement can be reopened", 409)
    lock = _lock(db, engagement.id)
    if lock.state != "LOCKED":
        raise ApiError("ENGAGEMENT_LOCK_STATE_INVALID", "Closed engagement is not locked as expected", 409)
    blockers = _blockers(db, engagement.id)
    old = engagement.status
    engagement.status = "REOPENED"
    engagement.version += 1
    lock.state = "OPEN"
    lock.reopen_requested_by_user_id = user.id
    lock.reopen_reason = payload.reason
    lock.reopened_by_user_id = user.id
    lock.reopened_at = datetime.now(timezone.utc)
    lock.revision_number += 1
    _record(db, request, user, engagement, "ENGAGEMENT_REOPENED", old, engagement.status, payload.reason, blockers, lock.revision_number)
    db.commit()
    return _view(db, engagement)


@router.get("/{engagement_id}/history", response_model=list[EngagementReviewActionView])
def review_history(
    engagement_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> list[EngagementReviewActionView]:
    _accessible_engagement(db, user, engagement_id, Permission.ENGAGEMENT_VIEW)
    rows = list(
        db.scalars(
            select(EngagementReviewAction)
            .where(EngagementReviewAction.engagement_id == engagement_id)
            .order_by(EngagementReviewAction.created_at, EngagementReviewAction.id)
        )
    )
    return [EngagementReviewActionView.model_validate(item) for item in rows]
