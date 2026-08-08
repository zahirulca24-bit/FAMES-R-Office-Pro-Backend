from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_execution_models import AuditCompletion, AuditCompletionAction, AuditIssue, AuditRequisition, AuditTest
from app.audit_execution_schemas import (
    AuditIssueCreateRequest,
    AuditIssueResolveRequest,
    AuditIssueView,
    AuditTestCompleteRequest,
    AuditTestCreateRequest,
    AuditTestView,
    CompletionActionView,
    CompletionUpsertRequest,
    CompletionView,
    FinalizationReadinessView,
    RequisitionCreateRequest,
    RequisitionStatusRequest,
    RequisitionView,
)
from app.audit_models import AuditAcceptance, AuditIndependenceDeclaration, AuditMateriality, AuditRisk, AuditRiskProcedure
from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement, EngagementTeamMember
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile
from app.working_paper_models import WorkingPaper
from app.workflow_models import RecordLock

router = APIRouter(prefix="/api/v1/audit-execution", tags=["audit-execution"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _engagement(db: Session, engagement_id: str) -> Engagement:
    row = db.get(Engagement, engagement_id)
    if row is None or row.is_archived:
        raise ApiError("ENGAGEMENT_NOT_FOUND", "Engagement not found", 404)
    return row


def _can_access(db: Session, user: AuthUser, engagement: Engagement) -> bool:
    if user.role == "SUPER_ADMIN" or engagement.partner_user_id == user.id or engagement.manager_user_id == user.id:
        return True
    team = db.scalar(
        select(EngagementTeamMember.id)
        .join(StaffProfile, StaffProfile.id == EngagementTeamMember.staff_id)
        .where(
            EngagementTeamMember.engagement_id == engagement.id,
            EngagementTeamMember.status == "ACTIVE",
            StaffProfile.auth_user_id == user.id,
            StaffProfile.is_archived.is_(False),
        )
        .limit(1)
    )
    return team is not None


def _accessible(db: Session, user: AuthUser, engagement_id: str, permission: Permission) -> Engagement:
    _require(user, permission)
    engagement = _engagement(db, engagement_id)
    if not _can_access(db, user, engagement):
        raise ApiError("AUDIT_ENGAGEMENT_ACCESS_DENIED", "You do not have access to this engagement", 403)
    return engagement


def _ensure_not_finalized(db: Session, engagement_id: str) -> None:
    completion = db.scalar(select(AuditCompletion).where(AuditCompletion.engagement_id == engagement_id))
    if completion is not None and completion.is_locked:
        raise ApiError("AUDIT_FILE_LOCKED", "The audit file is finalized and locked", 409)


def _event(db: Session, request: Request, user: AuthUser, engagement_id: str, event_type: str, detail: dict[str, object]) -> None:
    payload = json.dumps(detail, default=str)
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="AUDIT_FILE", resource_id=engagement_id, summary=event_type.replace("_", " ").title(), detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="AUDIT_FILE", resource_id=engagement_id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


def _planning_ready(db: Session, engagement_id: str) -> tuple[bool, int]:
    acceptance = db.scalar(select(AuditAcceptance).where(AuditAcceptance.engagement_id == engagement_id))
    materiality = db.scalar(select(AuditMateriality).where(AuditMateriality.engagement_id == engagement_id))
    active_team = int(db.scalar(select(func.count()).select_from(EngagementTeamMember).where(EngagementTeamMember.engagement_id == engagement_id, EngagementTeamMember.status == "ACTIVE")) or 0)
    declarations = list(db.scalars(select(AuditIndependenceDeclaration).where(AuditIndependenceDeclaration.engagement_id == engagement_id)))
    independence_ok = active_team > 0 and len(declarations) >= active_team and all(row.status == "CLEAR" for row in declarations)
    acceptance_ok = acceptance is not None and acceptance.status == "APPROVED"
    materiality_ok = materiality is not None and materiality.overall_materiality_minor > 0
    significant = list(db.scalars(select(AuditRisk).where(AuditRisk.engagement_id == engagement_id, AuditRisk.significant_risk.is_(True), AuditRisk.status == "OPEN")))
    without_procedure = 0
    for risk in significant:
        if db.scalar(select(AuditRiskProcedure.id).where(AuditRiskProcedure.risk_id == risk.id).limit(1)) is None:
            without_procedure += 1
    return acceptance_ok and independence_ok and materiality_ok, without_procedure


def _readiness(db: Session, engagement_id: str) -> FinalizationReadinessView:
    planning_ready, significant_without_procedure = _planning_ready(db, engagement_id)
    completion = db.scalar(select(AuditCompletion).where(AuditCompletion.engagement_id == engagement_id))
    checklist_ready = bool(
        completion
        and completion.subsequent_events_done
        and completion.going_concern_done
        and completion.misstatements_evaluated
        and completion.representation_letter_obtained
        and completion.quality_review_done
    )
    open_requisitions = int(db.scalar(select(func.count()).select_from(AuditRequisition).where(AuditRequisition.engagement_id == engagement_id, AuditRequisition.status != "CLOSED")) or 0)
    incomplete_tests = int(db.scalar(select(func.count()).select_from(AuditTest).where(AuditTest.engagement_id == engagement_id, AuditTest.status != "COMPLETED")) or 0)
    open_high = int(db.scalar(select(func.count()).select_from(AuditIssue).where(AuditIssue.engagement_id == engagement_id, AuditIssue.status == "OPEN", AuditIssue.severity.in_(["HIGH", "CRITICAL"]))) or 0)
    open_other = int(db.scalar(select(func.count()).select_from(AuditIssue).where(AuditIssue.engagement_id == engagement_id, AuditIssue.status == "OPEN", AuditIssue.severity.in_(["LOW", "MEDIUM"]))) or 0)
    unlocked_papers = int(db.scalar(select(func.count()).select_from(WorkingPaper).where(WorkingPaper.engagement_id == engagement_id, WorkingPaper.is_locked.is_(False))) or 0)
    ready = planning_ready and checklist_ready and open_requisitions == 0 and incomplete_tests == 0 and open_high == 0 and unlocked_papers == 0 and significant_without_procedure == 0
    return FinalizationReadinessView(
        engagement_id=engagement_id,
        ready=ready,
        planning_ready=planning_ready,
        completion_checklist_ready=checklist_ready,
        open_requisitions=open_requisitions,
        incomplete_tests=incomplete_tests,
        open_high_risk_issues=open_high,
        open_other_issues=open_other,
        unlocked_working_papers=unlocked_papers,
        significant_risks_without_procedure=significant_without_procedure,
    )


@router.post("/{engagement_id}/requisitions", response_model=RequisitionView, status_code=status.HTTP_201_CREATED)
def create_requisition(engagement_id: str, payload: RequisitionCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> RequisitionView:
    _accessible(db, user, engagement_id, Permission.AUDIT_EXECUTE)
    _ensure_not_finalized(db, engagement_id)
    if db.scalar(select(AuditRequisition.id).where(AuditRequisition.engagement_id == engagement_id, AuditRequisition.requisition_code == payload.requisition_code)):
        raise ApiError("AUDIT_REQUISITION_DUPLICATE", "Requisition code already exists", 409)
    row = AuditRequisition(engagement_id=engagement_id, created_by_user_id=user.id, **payload.model_dump())
    db.add(row)
    _event(db, request, user, engagement_id, "AUDIT_REQUISITION_CREATED", {"code": payload.requisition_code})
    db.commit(); db.refresh(row)
    return RequisitionView.model_validate(row)


@router.post("/requisitions/{requisition_id}/status", response_model=RequisitionView)
def update_requisition_status(requisition_id: str, payload: RequisitionStatusRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> RequisitionView:
    row = db.get(AuditRequisition, requisition_id)
    if row is None: raise ApiError("AUDIT_REQUISITION_NOT_FOUND", "Requisition not found", 404)
    _accessible(db, user, row.engagement_id, Permission.AUDIT_EXECUTE); _ensure_not_finalized(db, row.engagement_id)
    if row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Requisition has changed", 409, {"current_version": row.version})
    row.status = payload.status; row.response_note = payload.response_note; row.version += 1
    if payload.status in {"RECEIVED", "CLOSED"}:
        row.received_by_user_id = user.id; row.received_at = row.received_at or _now()
    _event(db, request, user, row.engagement_id, "AUDIT_REQUISITION_STATUS_CHANGED", {"code": row.requisition_code, "status": row.status})
    db.commit(); db.refresh(row)
    return RequisitionView.model_validate(row)


@router.post("/{engagement_id}/tests", response_model=AuditTestView, status_code=status.HTTP_201_CREATED)
def create_test(engagement_id: str, payload: AuditTestCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AuditTestView:
    _accessible(db, user, engagement_id, Permission.AUDIT_EXECUTE); _ensure_not_finalized(db, engagement_id)
    if payload.risk_id:
        risk = db.get(AuditRisk, payload.risk_id)
        if risk is None or risk.engagement_id != engagement_id: raise ApiError("AUDIT_TEST_RISK_MISMATCH", "Risk must belong to this engagement", 422)
    if payload.working_paper_id:
        paper = db.get(WorkingPaper, payload.working_paper_id)
        if paper is None or paper.engagement_id != engagement_id: raise ApiError("AUDIT_TEST_PAPER_MISMATCH", "Working paper must belong to this engagement", 422)
    if db.scalar(select(AuditTest.id).where(AuditTest.engagement_id == engagement_id, AuditTest.test_code == payload.test_code)):
        raise ApiError("AUDIT_TEST_DUPLICATE", "Test code already exists", 409)
    row = AuditTest(engagement_id=engagement_id, performed_by_user_id=user.id, **payload.model_dump())
    db.add(row); _event(db, request, user, engagement_id, "AUDIT_TEST_CREATED", {"test_code": row.test_code})
    db.commit(); db.refresh(row); return AuditTestView.model_validate(row)


@router.post("/tests/{test_id}/complete", response_model=AuditTestView)
def complete_test(test_id: str, payload: AuditTestCompleteRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AuditTestView:
    row = db.get(AuditTest, test_id)
    if row is None: raise ApiError("AUDIT_TEST_NOT_FOUND", "Audit test not found", 404)
    _accessible(db, user, row.engagement_id, Permission.AUDIT_EXECUTE); _ensure_not_finalized(db, row.engagement_id)
    if row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Audit test has changed", 409, {"current_version": row.version})
    if payload.exceptions_count > row.sample_size and row.sample_size > 0: raise ApiError("AUDIT_TEST_INVALID_EXCEPTIONS", "Exceptions cannot exceed sample size", 422)
    row.exceptions_count = payload.exceptions_count; row.conclusion = payload.conclusion; row.status = "COMPLETED"; row.completed_at = _now(); row.version += 1
    _event(db, request, user, row.engagement_id, "AUDIT_TEST_COMPLETED", {"test_code": row.test_code, "exceptions": row.exceptions_count})
    db.commit(); db.refresh(row); return AuditTestView.model_validate(row)


@router.post("/{engagement_id}/issues", response_model=AuditIssueView, status_code=status.HTTP_201_CREATED)
def create_issue(engagement_id: str, payload: AuditIssueCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AuditIssueView:
    _accessible(db, user, engagement_id, Permission.AUDIT_EXECUTE); _ensure_not_finalized(db, engagement_id)
    if payload.risk_id:
        risk = db.get(AuditRisk, payload.risk_id)
        if risk is None or risk.engagement_id != engagement_id: raise ApiError("AUDIT_ISSUE_RISK_MISMATCH", "Risk must belong to this engagement", 422)
    if db.scalar(select(AuditIssue.id).where(AuditIssue.engagement_id == engagement_id, AuditIssue.issue_code == payload.issue_code)):
        raise ApiError("AUDIT_ISSUE_DUPLICATE", "Issue code already exists", 409)
    row = AuditIssue(engagement_id=engagement_id, raised_by_user_id=user.id, **payload.model_dump())
    db.add(row); _event(db, request, user, engagement_id, "AUDIT_ISSUE_RAISED", {"issue_code": row.issue_code, "severity": row.severity})
    db.commit(); db.refresh(row); return AuditIssueView.model_validate(row)


@router.post("/issues/{issue_id}/resolve", response_model=AuditIssueView)
def resolve_issue(issue_id: str, payload: AuditIssueResolveRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AuditIssueView:
    row = db.get(AuditIssue, issue_id)
    if row is None: raise ApiError("AUDIT_ISSUE_NOT_FOUND", "Audit issue not found", 404)
    _accessible(db, user, row.engagement_id, Permission.AUDIT_EXECUTE); _ensure_not_finalized(db, row.engagement_id)
    if row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Audit issue has changed", 409, {"current_version": row.version})
    row.status = "RESOLVED"; row.resolution = payload.resolution; row.resolved_by_user_id = user.id; row.resolved_at = _now(); row.version += 1
    _event(db, request, user, row.engagement_id, "AUDIT_ISSUE_RESOLVED", {"issue_code": row.issue_code})
    db.commit(); db.refresh(row); return AuditIssueView.model_validate(row)


@router.put("/{engagement_id}/completion", response_model=CompletionView)
def upsert_completion(engagement_id: str, payload: CompletionUpsertRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> CompletionView:
    _accessible(db, user, engagement_id, Permission.AUDIT_EXECUTE); _ensure_not_finalized(db, engagement_id)
    row = db.scalar(select(AuditCompletion).where(AuditCompletion.engagement_id == engagement_id))
    values = payload.model_dump(exclude={"expected_version"})
    if row is None:
        row = AuditCompletion(engagement_id=engagement_id, created_by_user_id=user.id, **values); db.add(row)
    else:
        if payload.expected_version is None or row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Completion checklist has changed", 409, {"current_version": row.version})
        for key, value in values.items(): setattr(row, key, value)
        row.version += 1
    row.status = "READY" if all(values.values()) else "DRAFT"
    _event(db, request, user, engagement_id, "AUDIT_COMPLETION_UPDATED", {"status": row.status})
    db.commit(); db.refresh(row); return CompletionView.model_validate(row)


@router.get("/{engagement_id}/finalization-readiness", response_model=FinalizationReadinessView)
def finalization_readiness(engagement_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> FinalizationReadinessView:
    _accessible(db, user, engagement_id, Permission.AUDIT_EXECUTE)
    return _readiness(db, engagement_id)


@router.post("/{engagement_id}/finalize", response_model=CompletionView)
def finalize_audit_file(engagement_id: str, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> CompletionView:
    _accessible(db, user, engagement_id, Permission.AUDIT_FINALIZE)
    completion = db.scalar(select(AuditCompletion).where(AuditCompletion.engagement_id == engagement_id))
    if completion is None: raise ApiError("AUDIT_COMPLETION_MISSING", "Completion checklist must be completed before finalization", 409)
    if completion.is_locked: raise ApiError("AUDIT_FILE_LOCKED", "Audit file is already finalized and locked", 409)
    readiness = _readiness(db, engagement_id)
    if not readiness.ready:
        raise ApiError("AUDIT_FINALIZATION_BLOCKED", "Audit file has unresolved finalization blockers", 409, readiness.model_dump())
    completion.status = "FINALIZED"; completion.is_locked = True; completion.finalized_by_user_id = user.id; completion.finalized_at = _now(); completion.version += 1
    lock = db.scalar(select(RecordLock).where(RecordLock.resource_type == "AUDIT_FILE", RecordLock.resource_id == engagement_id))
    if lock is None:
        lock = RecordLock(resource_type="AUDIT_FILE", resource_id=engagement_id, state="LOCKED", locked_by_user_id=user.id, locked_at=_now()); db.add(lock)
    else:
        lock.state = "LOCKED"; lock.locked_by_user_id = user.id; lock.locked_at = _now()
    detail = readiness.model_dump(); detail["finalized_at"] = completion.finalized_at.isoformat()
    db.add(AuditCompletionAction(engagement_id=engagement_id, action="FINALIZED_AND_LOCKED", actor_user_id=user.id, detail_json=json.dumps(detail, default=str)))
    _event(db, request, user, engagement_id, "AUDIT_FILE_FINALIZED", detail)
    db.commit(); db.refresh(completion); return CompletionView.model_validate(completion)


@router.get("/{engagement_id}/completion-history", response_model=list[CompletionActionView])
def completion_history(engagement_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[CompletionActionView]:
    _accessible(db, user, engagement_id, Permission.AUDIT_EXECUTE)
    rows = list(db.scalars(select(AuditCompletionAction).where(AuditCompletionAction.engagement_id == engagement_id).order_by(AuditCompletionAction.created_at.desc())))
    return [CompletionActionView.model_validate(row) for row in rows]
