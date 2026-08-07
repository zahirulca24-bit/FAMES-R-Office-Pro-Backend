from __future__ import annotations

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement
from app.engagement_template_models import (
    EngagementGeneratedTask,
    EngagementRequiredDocument,
    EngagementTemplate,
    EngagementTemplateDocument,
    EngagementTemplateTask,
)
from app.engagement_template_schemas import (
    EngagementTemplateApplyRequest,
    EngagementTemplateCreateRequest,
    EngagementTemplateView,
    GeneratedTaskView,
    RequiredDocumentView,
    TemplateApplyResult,
)
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser

router = APIRouter(prefix="/api/v1/engagement-templates", tags=["engagement-templates"])


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _event(db: Session, request: Request, user: AuthUser, engagement_id: str, event_type: str, summary: str, detail: dict[str, object]) -> None:
    cid = correlation_id_from_request(request)
    payload = json.dumps(detail, default=str)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="ENGAGEMENT", resource_id=engagement_id, summary=summary, detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="ENGAGEMENT", resource_id=engagement_id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


@router.post("", response_model=EngagementTemplateView, status_code=status.HTTP_201_CREATED)
def create_template(payload: EngagementTemplateCreateRequest, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> EngagementTemplateView:
    _require(user, Permission.ENGAGEMENT_CREATE)
    template = EngagementTemplate(code=payload.code, name=payload.name.strip(), service_type=payload.service_type, description=payload.description, created_by_user_id=user.id)
    db.add(template)
    db.flush()
    for item in payload.tasks:
        db.add(EngagementTemplateTask(template_id=template.id, **item.model_dump()))
    for item in payload.required_documents:
        db.add(EngagementTemplateDocument(template_id=template.id, **item.model_dump()))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("ENGAGEMENT_TEMPLATE_CONFLICT", "Template code or child code is duplicated", 409) from exc
    db.refresh(template)
    return EngagementTemplateView.model_validate(template)


@router.get("", response_model=list[EngagementTemplateView])
def list_templates(service_type: str | None = None, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[EngagementTemplateView]:
    _require(user, Permission.ENGAGEMENT_VIEW)
    stmt = select(EngagementTemplate).where(EngagementTemplate.status == "ACTIVE")
    if service_type:
        stmt = stmt.where(EngagementTemplate.service_type == service_type.strip().upper())
    return [EngagementTemplateView.model_validate(x) for x in db.scalars(stmt.order_by(EngagementTemplate.name))]


@router.post("/engagements/{engagement_id}/apply", response_model=TemplateApplyResult)
def apply_template(engagement_id: str, payload: EngagementTemplateApplyRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> TemplateApplyResult:
    _require(user, Permission.ENGAGEMENT_ASSIGN)
    engagement = db.get(Engagement, engagement_id)
    if engagement is None or engagement.is_archived:
        raise ApiError("ENGAGEMENT_NOT_FOUND", "Engagement not found", 404)
    if user.role != "SUPER_ADMIN" and user.id not in {engagement.partner_user_id, engagement.manager_user_id}:
        raise ApiError("ENGAGEMENT_ACCESS_DENIED", "Only engagement leads may apply templates", 403)
    if engagement.version != payload.expected_engagement_version:
        raise ApiError("VERSION_CONFLICT", "Engagement record has changed; reload before applying template", 409, {"current_version": engagement.version})
    template = db.get(EngagementTemplate, payload.template_id)
    if template is None or template.status != "ACTIVE":
        raise ApiError("ENGAGEMENT_TEMPLATE_NOT_FOUND", "Active engagement template not found", 404)
    if template.service_type != engagement.service_type:
        raise ApiError("TEMPLATE_SERVICE_MISMATCH", "Template service type does not match engagement", 409)
    existing = db.scalar(select(EngagementGeneratedTask.id).where(EngagementGeneratedTask.engagement_id == engagement.id).limit(1))
    if existing:
        raise ApiError("ENGAGEMENT_TEMPLATE_ALREADY_APPLIED", "This engagement already has generated template tasks", 409)

    anchor = payload.anchor_date or engagement.period_start or engagement.deadline
    tasks = list(db.scalars(select(EngagementTemplateTask).where(EngagementTemplateTask.template_id == template.id).order_by(EngagementTemplateTask.sequence)))
    docs = list(db.scalars(select(EngagementTemplateDocument).where(EngagementTemplateDocument.template_id == template.id).order_by(EngagementTemplateDocument.stage, EngagementTemplateDocument.title)))
    generated: list[EngagementGeneratedTask] = []
    required_docs: list[EngagementRequiredDocument] = []
    for item in tasks:
        due_date = anchor + timedelta(days=item.due_offset_days) if anchor and item.due_offset_days is not None else None
        row = EngagementGeneratedTask(engagement_id=engagement.id, template_task_id=item.id, task_code=item.task_code, title=item.title, stage=item.stage, sequence=item.sequence, due_date=due_date, assignment_role=item.default_assignment_role, approval_role=item.approval_role, required=item.required)
        db.add(row)
        generated.append(row)
    for item in docs:
        row = EngagementRequiredDocument(engagement_id=engagement.id, template_document_id=item.id, document_code=item.document_code, title=item.title, stage=item.stage, required=item.required)
        db.add(row)
        required_docs.append(row)
    engagement.version += 1
    engagement.updated_by_user_id = user.id
    _event(db, request, user, engagement.id, "ENGAGEMENT_TEMPLATE_APPLIED", f"Template {template.code} applied to {engagement.engagement_code}", {"template_id": template.id, "task_count": len(generated), "document_count": len(required_docs)})
    db.commit()
    for row in generated + required_docs:
        db.refresh(row)
    return TemplateApplyResult(engagement_id=engagement.id, template_id=template.id, generated_tasks=[GeneratedTaskView.model_validate(x) for x in generated], required_documents=[RequiredDocumentView.model_validate(x) for x in required_docs])


@router.get("/engagements/{engagement_id}/tasks", response_model=list[GeneratedTaskView])
def list_generated_tasks(engagement_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[GeneratedTaskView]:
    _require(user, Permission.ENGAGEMENT_VIEW)
    engagement = db.get(Engagement, engagement_id)
    if engagement is None:
        raise ApiError("ENGAGEMENT_NOT_FOUND", "Engagement not found", 404)
    rows = db.scalars(select(EngagementGeneratedTask).where(EngagementGeneratedTask.engagement_id == engagement_id).order_by(EngagementGeneratedTask.sequence))
    return [GeneratedTaskView.model_validate(x) for x in rows]
