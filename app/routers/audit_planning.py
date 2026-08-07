from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_models import AuditAcceptance, AuditIndependenceDeclaration, AuditMateriality, AuditRisk, AuditRiskProcedure
from app.audit_schemas import AcceptanceDecisionRequest, AcceptanceUpsertRequest, AcceptanceView, IndependenceUpsertRequest, IndependenceView, MaterialityUpsertRequest, MaterialityView, PlanningReadinessView, RiskCreateRequest, RiskProcedureLinkRequest, RiskView
from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement, EngagementTeamMember
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile
from app.working_paper_models import WorkingPaper

router = APIRouter(prefix="/api/v1/audit-planning", tags=["audit-planning"])


def _now() -> datetime: return datetime.now(timezone.utc)

def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission): raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)

def _engagement(db: Session, engagement_id: str) -> Engagement:
    row = db.get(Engagement, engagement_id)
    if row is None or row.is_archived: raise ApiError("ENGAGEMENT_NOT_FOUND", "Engagement not found", 404)
    return row

def _can_access(db: Session, user: AuthUser, engagement: Engagement) -> bool:
    if user.role == "SUPER_ADMIN" or engagement.partner_user_id == user.id or engagement.manager_user_id == user.id: return True
    team = db.scalar(select(EngagementTeamMember.id).join(StaffProfile, StaffProfile.id == EngagementTeamMember.staff_id).where(EngagementTeamMember.engagement_id == engagement.id, EngagementTeamMember.status == "ACTIVE", StaffProfile.auth_user_id == user.id, StaffProfile.is_archived.is_(False)).limit(1))
    return team is not None

def _accessible(db: Session, user: AuthUser, engagement_id: str, permission: Permission) -> Engagement:
    _require(user, permission); engagement = _engagement(db, engagement_id)
    if not _can_access(db, user, engagement): raise ApiError("AUDIT_ENGAGEMENT_ACCESS_DENIED", "You do not have access to this engagement", 403)
    return engagement

def _event(db: Session, request: Request, user: AuthUser, engagement_id: str, event_type: str, detail: dict[str, object]) -> None:
    payload = json.dumps(detail, default=str); cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="ENGAGEMENT", resource_id=engagement_id, summary=event_type.replace("_", " ").title(), detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="ENGAGEMENT", resource_id=engagement_id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


@router.put("/{engagement_id}/acceptance", response_model=AcceptanceView)
def upsert_acceptance(engagement_id: str, payload: AcceptanceUpsertRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AcceptanceView:
    _accessible(db, user, engagement_id, Permission.AUDIT_PLAN)
    row = db.scalar(select(AuditAcceptance).where(AuditAcceptance.engagement_id == engagement_id))
    if row is None:
        row = AuditAcceptance(engagement_id=engagement_id, created_by_user_id=user.id, version=1); db.add(row)
    else:
        if payload.expected_version is None or row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Acceptance record has changed; reload before updating", 409, {"current_version": row.version})
        row.version += 1
    row.continuance = payload.continuance; row.integrity_assessment = payload.integrity_assessment; row.competence_resources = payload.competence_resources; row.preconditions_met = payload.preconditions_met; row.reason = payload.reason; row.status = "DRAFT"
    _event(db, request, user, engagement_id, "AUDIT_ACCEPTANCE_UPDATED", {"status": row.status}); db.commit(); db.refresh(row)
    return AcceptanceView.model_validate(row)


@router.post("/{engagement_id}/acceptance/decision", response_model=AcceptanceView)
def decide_acceptance(engagement_id: str, payload: AcceptanceDecisionRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AcceptanceView:
    _accessible(db, user, engagement_id, Permission.AUDIT_APPROVE)
    row = db.scalar(select(AuditAcceptance).where(AuditAcceptance.engagement_id == engagement_id))
    if row is None: raise ApiError("AUDIT_ACCEPTANCE_MISSING", "Acceptance assessment must be completed first", 409)
    if row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Acceptance record has changed", 409, {"current_version": row.version})
    if payload.decision == "APPROVED" and not row.preconditions_met: raise ApiError("AUDIT_PRECONDITIONS_NOT_MET", "Audit preconditions must be met before acceptance approval", 409)
    row.status = payload.decision; row.reason = payload.reason; row.version += 1; row.approved_by_user_id = user.id if payload.decision == "APPROVED" else None; row.approved_at = _now() if payload.decision == "APPROVED" else None
    _event(db, request, user, engagement_id, "AUDIT_ACCEPTANCE_DECIDED", {"decision": payload.decision}); db.commit(); db.refresh(row)
    return AcceptanceView.model_validate(row)


@router.put("/{engagement_id}/independence", response_model=IndependenceView)
def upsert_independence(engagement_id: str, payload: IndependenceUpsertRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> IndependenceView:
    _accessible(db, user, engagement_id, Permission.AUDIT_PLAN)
    member = db.scalar(select(EngagementTeamMember.id).where(EngagementTeamMember.engagement_id == engagement_id, EngagementTeamMember.staff_id == payload.staff_id, EngagementTeamMember.status == "ACTIVE"))
    if member is None: raise ApiError("AUDIT_STAFF_NOT_ON_TEAM", "Independence declaration requires an active engagement team member", 422)
    row = db.scalar(select(AuditIndependenceDeclaration).where(AuditIndependenceDeclaration.engagement_id == engagement_id, AuditIndependenceDeclaration.staff_id == payload.staff_id))
    if row is None: row = AuditIndependenceDeclaration(engagement_id=engagement_id, staff_id=payload.staff_id, declared_by_user_id=user.id); db.add(row)
    row.status = payload.status; row.threat_details = payload.threat_details; row.safeguards = payload.safeguards; row.declared_by_user_id = user.id; row.declared_at = _now()
    _event(db, request, user, engagement_id, "AUDIT_INDEPENDENCE_DECLARED", {"staff_id": payload.staff_id, "status": payload.status}); db.commit(); db.refresh(row)
    return IndependenceView.model_validate(row)


@router.put("/{engagement_id}/materiality", response_model=MaterialityView)
def upsert_materiality(engagement_id: str, payload: MaterialityUpsertRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> MaterialityView:
    _accessible(db, user, engagement_id, Permission.AUDIT_PLAN)
    if payload.performance_materiality_minor > payload.overall_materiality_minor: raise ApiError("INVALID_MATERIALITY", "Performance materiality cannot exceed overall materiality", 422)
    row = db.scalar(select(AuditMateriality).where(AuditMateriality.engagement_id == engagement_id))
    data = payload.model_dump(exclude={"expected_version"})
    if row is None: row = AuditMateriality(engagement_id=engagement_id, created_by_user_id=user.id, version=1, **data); db.add(row)
    else:
        if payload.expected_version is None or row.version != payload.expected_version: raise ApiError("VERSION_CONFLICT", "Materiality record has changed", 409, {"current_version": row.version})
        for key, value in data.items(): setattr(row, key, value)
        row.version += 1
    _event(db, request, user, engagement_id, "AUDIT_MATERIALITY_UPDATED", {"overall_materiality_minor": payload.overall_materiality_minor}); db.commit(); db.refresh(row)
    return MaterialityView.model_validate(row)


@router.post("/{engagement_id}/risks", response_model=RiskView, status_code=status.HTTP_201_CREATED)
def create_risk(engagement_id: str, payload: RiskCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> RiskView:
    _accessible(db, user, engagement_id, Permission.AUDIT_PLAN)
    if db.scalar(select(AuditRisk.id).where(AuditRisk.engagement_id == engagement_id, AuditRisk.risk_code == payload.risk_code)): raise ApiError("AUDIT_RISK_DUPLICATE", "Risk code already exists for this engagement", 409)
    row = AuditRisk(engagement_id=engagement_id, created_by_user_id=user.id, **payload.model_dump()); db.add(row); _event(db, request, user, engagement_id, "AUDIT_RISK_CREATED", {"risk_code": payload.risk_code}); db.commit(); db.refresh(row)
    return RiskView.model_validate(row)


@router.post("/risks/{risk_id}/procedures", status_code=status.HTTP_201_CREATED)
def link_risk_procedure(risk_id: str, payload: RiskProcedureLinkRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> dict[str, str]:
    risk = db.get(AuditRisk, risk_id)
    if risk is None: raise ApiError("AUDIT_RISK_NOT_FOUND", "Risk not found", 404)
    _accessible(db, user, risk.engagement_id, Permission.AUDIT_PLAN); paper = db.get(WorkingPaper, payload.working_paper_id)
    if paper is None or paper.engagement_id != risk.engagement_id: raise ApiError("AUDIT_PROCEDURE_ENGAGEMENT_MISMATCH", "Working paper must belong to the same engagement", 422)
    if db.scalar(select(AuditRiskProcedure.id).where(AuditRiskProcedure.risk_id == risk.id, AuditRiskProcedure.working_paper_id == paper.id)): raise ApiError("AUDIT_PROCEDURE_DUPLICATE", "Working paper already linked to this risk", 409)
    row = AuditRiskProcedure(risk_id=risk.id, working_paper_id=paper.id, procedure_note=payload.procedure_note); db.add(row); _event(db, request, user, risk.engagement_id, "AUDIT_RISK_PROCEDURE_LINKED", {"risk_id": risk.id, "working_paper_id": paper.id}); db.commit(); db.refresh(row)
    return {"id": row.id, "risk_id": risk.id, "working_paper_id": paper.id}


@router.get("/{engagement_id}/readiness", response_model=PlanningReadinessView)
def planning_readiness(engagement_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> PlanningReadinessView:
    _accessible(db, user, engagement_id, Permission.AUDIT_PLAN)
    acceptance = db.scalar(select(AuditAcceptance).where(AuditAcceptance.engagement_id == engagement_id)); materiality = db.scalar(select(AuditMateriality).where(AuditMateriality.engagement_id == engagement_id))
    active_team = int(db.scalar(select(func.count()).select_from(EngagementTeamMember).where(EngagementTeamMember.engagement_id == engagement_id, EngagementTeamMember.status == "ACTIVE")) or 0)
    declarations = list(db.scalars(select(AuditIndependenceDeclaration).where(AuditIndependenceDeclaration.engagement_id == engagement_id))); threats = sum(1 for row in declarations if row.status != "CLEAR")
    risks = list(db.scalars(select(AuditRisk).where(AuditRisk.engagement_id == engagement_id))); without_procedure = sum(1 for risk in risks if db.scalar(select(AuditRiskProcedure.id).where(AuditRiskProcedure.risk_id == risk.id).limit(1)) is None)
    independence_complete = active_team > 0 and len(declarations) >= active_team and threats == 0; acceptance_approved = acceptance is not None and acceptance.status == "APPROVED"; materiality_set = materiality is not None and materiality.overall_materiality_minor > 0
    return PlanningReadinessView(engagement_id=engagement_id, ready=acceptance_approved and independence_complete and materiality_set, acceptance_approved=acceptance_approved, independence_complete=independence_complete, materiality_set=materiality_set, open_independence_threats=threats, risks_count=len(risks), risks_without_procedure=without_procedure)
