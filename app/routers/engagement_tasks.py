from __future__ import annotations

import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement, EngagementTeamMember
from app.engagement_task_schemas import (
    DeadlineScanResult,
    TaskConfigureRequest,
    TaskDependencyCreateRequest,
    TaskDependencyView,
    TaskProgressSummary,
    TaskTransitionRequest,
    TaskView,
)
from app.engagement_template_models import (
    EngagementGeneratedTask,
    EngagementTaskDependency,
    EngagementTaskStatusHistory,
)
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile

router = APIRouter(prefix="/api/v1/engagement-tasks", tags=["engagement-tasks"])

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "NOT_STARTED": {"IN_PROGRESS", "BLOCKED", "CANCELLED"},
    "IN_PROGRESS": {"BLOCKED", "COMPLETED", "CANCELLED"},
    "BLOCKED": {"IN_PROGRESS", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _engagement_access(db: Session, user: AuthUser, engagement_id: str, permission: Permission) -> Engagement:
    _require(user, permission)
    engagement = db.get(Engagement, engagement_id)
    if engagement is None or engagement.is_archived:
        raise ApiError("ENGAGEMENT_NOT_FOUND", "Engagement not found", 404)
    if user.role == "SUPER_ADMIN" or engagement.partner_user_id == user.id or engagement.manager_user_id == user.id:
        return engagement
    assigned = db.scalar(
        select(EngagementTeamMember.id)
        .join(StaffProfile, StaffProfile.id == EngagementTeamMember.staff_id)
        .where(
            EngagementTeamMember.engagement_id == engagement_id,
            EngagementTeamMember.status == "ACTIVE",
            StaffProfile.auth_user_id == user.id,
        )
    )
    if assigned is None:
        raise ApiError("ENGAGEMENT_ACCESS_DENIED", "You do not have access to this engagement", 403)
    return engagement


def _task(db: Session, task_id: str) -> EngagementGeneratedTask:
    task = db.get(EngagementGeneratedTask, task_id)
    if task is None:
        raise ApiError("TASK_NOT_FOUND", "Engagement task not found", 404)
    return task


def _validate_staff(db: Session, staff_id: str | None, code: str) -> None:
    if staff_id is None:
        return
    staff = db.get(StaffProfile, staff_id)
    if staff is None or staff.is_archived or staff.employment_status != "ACTIVE":
        raise ApiError(code, "Staff member must be active and available", 422)


def _dependency_blockers(db: Session, task: EngagementGeneratedTask) -> list[str]:
    dependencies = list(
        db.scalars(select(EngagementTaskDependency).where(EngagementTaskDependency.task_id == task.id))
    )
    blockers: list[str] = []
    for dependency in dependencies:
        parent = db.get(EngagementGeneratedTask, dependency.depends_on_task_id)
        if parent is None or parent.status != "COMPLETED":
            blockers.append(dependency.depends_on_task_id)
    return blockers


def _would_create_cycle(db: Session, task_id: str, depends_on_task_id: str) -> bool:
    frontier = [depends_on_task_id]
    seen: set[str] = set()
    while frontier:
        current = frontier.pop()
        if current == task_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(
            db.scalars(
                select(EngagementTaskDependency.depends_on_task_id).where(
                    EngagementTaskDependency.task_id == current
                )
            ).all()
        )
    return False


def weighted_progress(tasks: list[EngagementGeneratedTask]) -> tuple[int, float, float]:
    total_weight = sum(max(int(task.weight_points or 0), 0) for task in tasks)
    if total_weight <= 0:
        return 0, 0.0, 0.0
    earned = sum(max(int(task.weight_points or 0), 0) * max(0, min(int(task.progress_percent or 0), 100)) / 100 for task in tasks)
    return total_weight, round(earned, 4), round((earned / total_weight) * 100, 2)


def _event(db: Session, request: Request, user: AuthUser, task: EngagementGeneratedTask, event_type: str, detail: dict[str, object]) -> None:
    payload = json.dumps(detail, default=str)
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="ENGAGEMENT_TASK", resource_id=task.id, summary=f"{task.task_code}: {event_type}", detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="ENGAGEMENT_TASK", resource_id=task.id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


@router.patch("/{task_id}", response_model=TaskView)
def configure_task(
    task_id: str,
    payload: TaskConfigureRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> TaskView:
    task = _task(db, task_id)
    _engagement_access(db, user, task.engagement_id, Permission.ENGAGEMENT_ASSIGN)
    if task.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Task has changed; reload before updating", 409, {"current_version": task.version})
    _validate_staff(db, payload.assignee_staff_id, "INVALID_ASSIGNEE")
    _validate_staff(db, payload.reviewer_staff_id, "INVALID_REVIEWER")
    if payload.parent_task_id:
        if payload.parent_task_id == task.id:
            raise ApiError("INVALID_PARENT_TASK", "Task cannot be its own parent", 422)
        parent = _task(db, payload.parent_task_id)
        if parent.engagement_id != task.engagement_id:
            raise ApiError("INVALID_PARENT_TASK", "Parent task must belong to the same engagement", 422)
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    for key, value in updates.items():
        setattr(task, key, value)
    task.version += 1
    _event(db, request, user, task, "ENGAGEMENT_TASK_CONFIGURED", updates)
    db.commit()
    db.refresh(task)
    return TaskView.model_validate(task)


@router.post("/{task_id}/dependencies", response_model=TaskDependencyView, status_code=status.HTTP_201_CREATED)
def create_dependency(
    task_id: str,
    payload: TaskDependencyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> TaskDependencyView:
    task = _task(db, task_id)
    _engagement_access(db, user, task.engagement_id, Permission.ENGAGEMENT_ASSIGN)
    dependency_task = _task(db, payload.depends_on_task_id)
    if dependency_task.engagement_id != task.engagement_id or dependency_task.id == task.id:
        raise ApiError("INVALID_TASK_DEPENDENCY", "Dependency must be a different task in the same engagement", 422)
    if _would_create_cycle(db, task.id, dependency_task.id):
        raise ApiError("TASK_DEPENDENCY_CYCLE", "Dependency would create a cycle", 409)
    row = EngagementTaskDependency(
        engagement_id=task.engagement_id,
        task_id=task.id,
        depends_on_task_id=dependency_task.id,
        dependency_type=payload.dependency_type,
        created_by_user_id=user.id,
    )
    db.add(row)
    _event(db, request, user, task, "ENGAGEMENT_TASK_DEPENDENCY_ADDED", {"depends_on_task_id": dependency_task.id})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("TASK_DEPENDENCY_EXISTS", "Dependency already exists", 409) from exc
    db.refresh(row)
    return TaskDependencyView.model_validate(row)


@router.post("/{task_id}/transition", response_model=TaskView)
def transition_task(
    task_id: str,
    payload: TaskTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> TaskView:
    task = _task(db, task_id)
    _engagement_access(db, user, task.engagement_id, Permission.ENGAGEMENT_ASSIGN)
    if task.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Task has changed; reload before updating", 409, {"current_version": task.version})
    if payload.to_status not in _ALLOWED_TRANSITIONS.get(task.status, set()):
        raise ApiError("INVALID_TASK_TRANSITION", f"Cannot move task from {task.status} to {payload.to_status}", 409)
    if payload.to_status in {"IN_PROGRESS", "COMPLETED"}:
        blockers = _dependency_blockers(db, task)
        if blockers:
            raise ApiError("TASK_DEPENDENCY_BLOCKED", "Task dependencies are not complete", 409, {"blocking_task_ids": blockers})
    previous = task.status
    task.status = payload.to_status
    if payload.to_status == "IN_PROGRESS":
        task.started_at = task.started_at or _utcnow()
        task.progress_percent = max(payload.progress_percent or task.progress_percent, 1)
    elif payload.to_status == "COMPLETED":
        task.progress_percent = 100
        task.completed_at = _utcnow()
        task.escalation_state = "NONE"
    elif payload.to_status == "BLOCKED":
        task.progress_percent = payload.progress_percent if payload.progress_percent is not None else task.progress_percent
    elif payload.to_status == "CANCELLED":
        task.progress_percent = payload.progress_percent if payload.progress_percent is not None else task.progress_percent
    task.version += 1
    db.add(EngagementTaskStatusHistory(task_id=task.id, from_status=previous, to_status=task.status, reason=payload.reason, actor_user_id=user.id))
    _event(db, request, user, task, "ENGAGEMENT_TASK_TRANSITIONED", {"from": previous, "to": task.status, "reason": payload.reason})
    db.commit()
    db.refresh(task)
    return TaskView.model_validate(task)


@router.get("/engagements/{engagement_id}/progress", response_model=TaskProgressSummary)
def engagement_progress(
    engagement_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> TaskProgressSummary:
    _engagement_access(db, user, engagement_id, Permission.ENGAGEMENT_VIEW)
    tasks = list(db.scalars(select(EngagementGeneratedTask).where(EngagementGeneratedTask.engagement_id == engagement_id)))
    today = date.today()
    total_weight, earned_weight, progress = weighted_progress(tasks)
    return TaskProgressSummary(
        engagement_id=engagement_id,
        total_tasks=len(tasks),
        completed_tasks=sum(1 for task in tasks if task.status == "COMPLETED"),
        blocked_tasks=sum(1 for task in tasks if task.status == "BLOCKED"),
        overdue_tasks=sum(1 for task in tasks if task.due_date and task.due_date < today and task.status not in {"COMPLETED", "CANCELLED"}),
        total_weight=total_weight,
        earned_weight=earned_weight,
        weighted_progress_percent=progress,
    )


@router.post("/engagements/{engagement_id}/deadline-scan", response_model=DeadlineScanResult)
def deadline_scan(
    engagement_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_password_changed),
) -> DeadlineScanResult:
    _engagement_access(db, user, engagement_id, Permission.ENGAGEMENT_ASSIGN)
    today = date.today()
    tasks = list(db.scalars(select(EngagementGeneratedTask).where(EngagementGeneratedTask.engagement_id == engagement_id)))
    escalated: list[str] = []
    for task in tasks:
        if task.due_date and task.due_date < today and task.status not in {"COMPLETED", "CANCELLED"}:
            if task.escalation_state != "OVERDUE":
                task.escalation_state = "OVERDUE"
                task.escalated_at = _utcnow()
                task.version += 1
                escalated.append(task.id)
                _event(db, request, user, task, "ENGAGEMENT_TASK_OVERDUE", {"due_date": task.due_date})
    db.commit()
    return DeadlineScanResult(engagement_id=engagement_id, escalated_task_ids=escalated, overdue_count=sum(1 for task in tasks if task.due_date and task.due_date < today and task.status not in {"COMPLETED", "CANCELLED"}))
