from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.document_models import Document, DocumentVersion
from app.engagement_models import Engagement, EngagementTeamMember
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile
from app.working_paper_models import WorkingPaper, WorkingPaperEvidence, WorkingPaperReviewNote, WorkingPaperSignoff
from app.working_paper_schemas import (
    EvidenceLinkRequest,
    EvidenceView,
    ReviewNoteCreateRequest,
    ReviewNoteResolveRequest,
    ReviewNoteView,
    SignoffRequest,
    SignoffView,
    WorkingPaperCreateRequest,
    WorkingPaperDetail,
    WorkingPaperListResponse,
    WorkingPaperUpdateRequest,
    WorkingPaperView,
)

router = APIRouter(prefix="/api/v1/working-papers", tags=["working-papers"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _can_access_engagement(db: Session, user: AuthUser, engagement_id: str) -> bool:
    engagement = db.get(Engagement, engagement_id)
    if engagement is None or engagement.is_archived:
        return False
    if user.role == "SUPER_ADMIN" or engagement.partner_user_id == user.id or engagement.manager_user_id == user.id:
        return True
    assigned = db.scalar(
        select(EngagementTeamMember.id)
        .join(StaffProfile, StaffProfile.id == EngagementTeamMember.staff_id)
        .where(
            EngagementTeamMember.engagement_id == engagement_id,
            EngagementTeamMember.status == "ACTIVE",
            StaffProfile.auth_user_id == user.id,
            StaffProfile.is_archived.is_(False),
        )
        .limit(1)
    )
    return assigned is not None


def _get_paper(db: Session, user: AuthUser, paper_id: str, permission: Permission) -> WorkingPaper:
    _require(user, permission)
    paper = db.get(WorkingPaper, paper_id)
    if paper is None:
        raise ApiError("WORKING_PAPER_NOT_FOUND", "Working paper not found", 404)
    if not _can_access_engagement(db, user, paper.engagement_id):
        raise ApiError("WORKING_PAPER_ACCESS_DENIED", "You do not have access to this working paper", 403)
    return paper


def _ensure_editable(paper: WorkingPaper) -> None:
    if paper.is_locked or paper.status == "LOCKED":
        raise ApiError("WORKING_PAPER_LOCKED", "Locked working papers cannot be modified", 409)


def _version_guard(paper: WorkingPaper, expected: int) -> None:
    if paper.version != expected:
        raise ApiError("VERSION_CONFLICT", "Working paper changed; reload before continuing", 409, {"current_version": paper.version})


def _event(db: Session, request: Request, user: AuthUser, paper: WorkingPaper, event_type: str, summary: str, detail: dict[str, object] | None = None) -> None:
    payload = json.dumps(detail or {}, default=str)
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="WORKING_PAPER", resource_id=paper.id, summary=summary, detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="WORKING_PAPER", resource_id=paper.id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


def _signoff(db: Session, paper: WorkingPaper, user: AuthUser, action: str, from_status: str, to_status: str, comment: str | None) -> None:
    db.add(WorkingPaperSignoff(working_paper_id=paper.id, action=action, from_status=from_status, to_status=to_status, actor_user_id=user.id, comment=(comment or "").strip() or None))


def _detail(db: Session, paper: WorkingPaper) -> WorkingPaperDetail:
    evidence = list(db.scalars(select(WorkingPaperEvidence).where(WorkingPaperEvidence.working_paper_id == paper.id).order_by(WorkingPaperEvidence.created_at)))
    notes = list(db.scalars(select(WorkingPaperReviewNote).where(WorkingPaperReviewNote.working_paper_id == paper.id).order_by(WorkingPaperReviewNote.created_at)))
    signoffs = list(db.scalars(select(WorkingPaperSignoff).where(WorkingPaperSignoff.working_paper_id == paper.id).order_by(WorkingPaperSignoff.created_at)))
    return WorkingPaperDetail(
        **WorkingPaperView.model_validate(paper).model_dump(),
        evidence=[EvidenceView.model_validate(item) for item in evidence],
        review_notes=[ReviewNoteView.model_validate(item) for item in notes],
        signoffs=[SignoffView.model_validate(item) for item in signoffs],
    )


@router.post("", response_model=WorkingPaperDetail, status_code=status.HTTP_201_CREATED)
def create_working_paper(payload: WorkingPaperCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    _require(user, Permission.WORKING_PAPER_PREPARE)
    if not _can_access_engagement(db, user, payload.engagement_id):
        raise ApiError("WORKING_PAPER_ACCESS_DENIED", "You do not have access to the engagement", 403)
    paper = WorkingPaper(
        engagement_id=payload.engagement_id,
        paper_code=payload.paper_code,
        title=payload.title.strip(),
        area=payload.area,
        objective=(payload.objective or "").strip() or None,
        conclusion=(payload.conclusion or "").strip() or None,
        prepared_by_user_id=user.id,
    )
    db.add(paper)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("WORKING_PAPER_CODE_CONFLICT", "paper_code already exists for this engagement", 409) from exc
    _signoff(db, paper, user, "PREPARED", "DRAFT", "DRAFT", "Working paper created")
    _event(db, request, user, paper, "WORKING_PAPER_CREATED", f"Working paper {paper.paper_code} created")
    db.commit()
    db.refresh(paper)
    return _detail(db, paper)


@router.get("", response_model=WorkingPaperListResponse)
def list_working_papers(engagement_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperListResponse:
    _require(user, Permission.ENGAGEMENT_VIEW)
    if not _can_access_engagement(db, user, engagement_id):
        raise ApiError("WORKING_PAPER_ACCESS_DENIED", "You do not have access to the engagement", 403)
    rows = list(db.scalars(select(WorkingPaper).where(WorkingPaper.engagement_id == engagement_id).order_by(WorkingPaper.paper_code)))
    return WorkingPaperListResponse(items=[WorkingPaperView.model_validate(row) for row in rows], total=len(rows))


@router.get("/{paper_id}", response_model=WorkingPaperDetail)
def get_working_paper(paper_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    paper = _get_paper(db, user, paper_id, Permission.ENGAGEMENT_VIEW)
    return _detail(db, paper)


@router.patch("/{paper_id}", response_model=WorkingPaperDetail)
def update_working_paper(paper_id: str, payload: WorkingPaperUpdateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_PREPARE)
    _ensure_editable(paper)
    _version_guard(paper, payload.expected_version)
    if paper.status not in {"DRAFT", "REVIEWED"}:
        raise ApiError("INVALID_WORKING_PAPER_STATE", "Working paper can only be edited in DRAFT or REVIEWED state", 409)
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(paper, field, value or None if field in {"objective", "conclusion"} else value)
    paper.version += 1
    _event(db, request, user, paper, "WORKING_PAPER_UPDATED", f"Working paper {paper.paper_code} updated", {"fields": sorted(updates)})
    db.commit()
    db.refresh(paper)
    return _detail(db, paper)


@router.post("/{paper_id}/evidence", response_model=EvidenceView, status_code=status.HTTP_201_CREATED)
def link_evidence(paper_id: str, payload: EvidenceLinkRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> EvidenceView:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_PREPARE)
    _ensure_editable(paper)
    _version_guard(paper, payload.expected_version)
    document = db.get(Document, payload.document_id)
    version = db.get(DocumentVersion, payload.document_version_id)
    if document is None or document.is_archived or document.resource_type != "ENGAGEMENT" or document.resource_id != paper.engagement_id:
        raise ApiError("INVALID_WORKING_PAPER_EVIDENCE", "Evidence document must belong to the same engagement", 422)
    if version is None or version.document_id != document.id:
        raise ApiError("INVALID_WORKING_PAPER_EVIDENCE_VERSION", "Document version does not belong to the evidence document", 422)
    link = WorkingPaperEvidence(
        working_paper_id=paper.id,
        document_id=document.id,
        document_version_id=version.id,
        evidence_role=payload.evidence_role,
        assertion=(payload.assertion or "").strip() or None,
        note=(payload.note or "").strip() or None,
        added_by_user_id=user.id,
    )
    db.add(link)
    paper.version += 1
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("WORKING_PAPER_EVIDENCE_EXISTS", "This document version is already linked", 409) from exc
    _event(db, request, user, paper, "WORKING_PAPER_EVIDENCE_LINKED", f"Evidence linked to {paper.paper_code}", {"document_id": document.id, "document_version_id": version.id})
    db.commit()
    db.refresh(link)
    return EvidenceView.model_validate(link)


@router.post("/{paper_id}/review-notes", response_model=ReviewNoteView, status_code=status.HTTP_201_CREATED)
def create_review_note(paper_id: str, payload: ReviewNoteCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ReviewNoteView:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_REVIEW)
    _ensure_editable(paper)
    note = WorkingPaperReviewNote(working_paper_id=paper.id, note_text=payload.note_text.strip(), raised_by_user_id=user.id)
    db.add(note)
    paper.version += 1
    db.flush()
    _event(db, request, user, paper, "WORKING_PAPER_REVIEW_NOTE_RAISED", f"Review note raised on {paper.paper_code}", {"review_note_id": note.id})
    db.commit()
    db.refresh(note)
    return ReviewNoteView.model_validate(note)


@router.post("/{paper_id}/review-notes/{note_id}/resolve", response_model=ReviewNoteView)
def resolve_review_note(paper_id: str, note_id: str, payload: ReviewNoteResolveRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ReviewNoteView:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_PREPARE)
    _ensure_editable(paper)
    _version_guard(paper, payload.expected_version)
    note = db.get(WorkingPaperReviewNote, note_id)
    if note is None or note.working_paper_id != paper.id:
        raise ApiError("REVIEW_NOTE_NOT_FOUND", "Review note not found", 404)
    if note.status == "RESOLVED":
        raise ApiError("REVIEW_NOTE_ALREADY_RESOLVED", "Review note is already resolved", 409)
    note.status = "RESOLVED"
    note.resolved_by_user_id = user.id
    note.resolution_note = payload.resolution_note.strip()
    note.resolved_at = _utcnow()
    paper.version += 1
    _event(db, request, user, paper, "WORKING_PAPER_REVIEW_NOTE_RESOLVED", f"Review note resolved on {paper.paper_code}", {"review_note_id": note.id})
    db.commit()
    db.refresh(note)
    return ReviewNoteView.model_validate(note)


def _transition(db: Session, request: Request, user: AuthUser, paper: WorkingPaper, payload: SignoffRequest, *, permission: Permission, expected_status: str, next_status: str, action: str) -> WorkingPaperDetail:
    _require(user, permission)
    _ensure_editable(paper)
    _version_guard(paper, payload.expected_version)
    if paper.status != expected_status:
        raise ApiError("INVALID_WORKING_PAPER_STATE", f"Expected {expected_status} before {action.lower()}", 409, {"current_status": paper.status})
    if action in {"APPROVED", "LOCKED"}:
        open_notes = int(db.scalar(select(func.count()).select_from(WorkingPaperReviewNote).where(WorkingPaperReviewNote.working_paper_id == paper.id, WorkingPaperReviewNote.status == "OPEN")) or 0)
        if open_notes:
            raise ApiError("OPEN_REVIEW_NOTES", "Resolve all review notes before approval/lock", 409, {"open_review_notes": open_notes})
    previous = paper.status
    paper.status = next_status
    paper.version += 1
    now = _utcnow()
    if action == "REVIEWED":
        paper.reviewed_by_user_id = user.id
        paper.reviewed_at = now
    elif action == "APPROVED":
        paper.approved_by_user_id = user.id
        paper.approved_at = now
    elif action == "LOCKED":
        paper.locked_by_user_id = user.id
        paper.locked_at = now
        paper.is_locked = True
    _signoff(db, paper, user, action, previous, next_status, payload.comment)
    _event(db, request, user, paper, f"WORKING_PAPER_{action}", f"Working paper {paper.paper_code} {action.lower()}")
    db.commit()
    db.refresh(paper)
    return _detail(db, paper)


@router.post("/{paper_id}/submit", response_model=WorkingPaperDetail)
def submit_working_paper(paper_id: str, payload: SignoffRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_SUBMIT)
    return _transition(db, request, user, paper, payload, permission=Permission.WORKING_PAPER_SUBMIT, expected_status="DRAFT", next_status="SUBMITTED", action="SUBMITTED")


@router.post("/{paper_id}/review", response_model=WorkingPaperDetail)
def review_working_paper(paper_id: str, payload: SignoffRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_REVIEW)
    return _transition(db, request, user, paper, payload, permission=Permission.WORKING_PAPER_REVIEW, expected_status="SUBMITTED", next_status="REVIEWED", action="REVIEWED")


@router.post("/{paper_id}/approve", response_model=WorkingPaperDetail)
def approve_working_paper(paper_id: str, payload: SignoffRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_APPROVE)
    return _transition(db, request, user, paper, payload, permission=Permission.WORKING_PAPER_APPROVE, expected_status="REVIEWED", next_status="APPROVED", action="APPROVED")


@router.post("/{paper_id}/lock", response_model=WorkingPaperDetail)
def lock_working_paper(paper_id: str, payload: SignoffRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorkingPaperDetail:
    paper = _get_paper(db, user, paper_id, Permission.WORKING_PAPER_LOCK)
    return _transition(db, request, user, paper, payload, permission=Permission.WORKING_PAPER_LOCK, expected_status="APPROVED", next_status="LOCKED", action="LOCKED")


@router.get("/{paper_id}/history", response_model=list[SignoffView])
def working_paper_history(paper_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[SignoffView]:
    paper = _get_paper(db, user, paper_id, Permission.ENGAGEMENT_VIEW)
    rows = list(db.scalars(select(WorkingPaperSignoff).where(WorkingPaperSignoff.working_paper_id == paper.id).order_by(WorkingPaperSignoff.created_at)))
    return [SignoffView.model_validate(row) for row in rows]
