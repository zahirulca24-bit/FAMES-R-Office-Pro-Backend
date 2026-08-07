from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile
from app.workforce_models import AttendanceRecord, CapacityAssignment, LeaveRecord, StaffWorklog
from app.workforce_schemas import (
    AttendanceCreateRequest,
    AttendanceView,
    CapacityAssignmentCreateRequest,
    CapacityAssignmentView,
    CapacitySummary,
    LeaveCreateRequest,
    LeaveView,
    WorklogCreateRequest,
    WorklogTransitionRequest,
    WorklogView,
)

router = APIRouter(prefix="/api/v1/workforce", tags=["workforce"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _staff(db: Session, staff_id: str) -> StaffProfile:
    staff = db.get(StaffProfile, staff_id)
    if staff is None or staff.is_archived:
        raise ApiError("STAFF_NOT_FOUND", "Staff not found", 404)
    return staff


def _event(db: Session, request: Request, user: AuthUser, staff_id: str, event_type: str, resource_id: str, summary: str) -> None:
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="STAFF", resource_id=staff_id, summary=summary))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="WORKFORCE", resource_id=resource_id, correlation_id=cid, outcome="SUCCESS"))


@router.post("/attendance", response_model=AttendanceView, status_code=status.HTTP_201_CREATED)
def create_attendance(payload: AttendanceCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> AttendanceView:
    _require(user, Permission.STAFF_MANAGE)
    _staff(db, payload.staff_id)
    row = AttendanceRecord(**payload.model_dump(), created_by_user_id=user.id)
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("ATTENDANCE_DUPLICATE", "Attendance already exists for this staff/date", 409) from exc
    _event(db, request, user, payload.staff_id, "ATTENDANCE_RECORDED", row.id, f"Attendance recorded for {payload.work_date}")
    db.commit()
    db.refresh(row)
    return AttendanceView.model_validate(row)


@router.post("/leave", response_model=LeaveView, status_code=status.HTTP_201_CREATED)
def create_leave(payload: LeaveCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> LeaveView:
    _require(user, Permission.STAFF_MANAGE)
    _staff(db, payload.staff_id)
    row = LeaveRecord(**payload.model_dump(), approved_by_user_id=user.id if payload.status == "APPROVED" else None)
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("LEAVE_DUPLICATE", "Leave record already exists for this staff/date/type", 409) from exc
    _event(db, request, user, payload.staff_id, "LEAVE_RECORDED", row.id, f"Leave recorded for {payload.leave_date}")
    db.commit()
    db.refresh(row)
    return LeaveView.model_validate(row)


@router.post("/assignments", response_model=CapacityAssignmentView, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: CapacityAssignmentCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> CapacityAssignmentView:
    _require(user, Permission.STAFF_MANAGE)
    _staff(db, payload.staff_id)
    row = CapacityAssignment(**payload.model_dump(), created_by_user_id=user.id)
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("ASSIGNMENT_DUPLICATE", "Capacity assignment already exists for this source/date", 409) from exc
    _event(db, request, user, payload.staff_id, "CAPACITY_ASSIGNED", row.id, f"Assigned {payload.assigned_minutes} minutes")
    db.commit()
    db.refresh(row)
    return CapacityAssignmentView.model_validate(row)


@router.post("/worklogs", response_model=WorklogView, status_code=status.HTTP_201_CREATED)
def create_worklog(payload: WorklogCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorklogView:
    _require(user, Permission.STAFF_MANAGE)
    _staff(db, payload.staff_id)
    row = StaffWorklog(**payload.model_dump(), created_by_user_id=user.id)
    db.add(row)
    db.flush()
    _event(db, request, user, payload.staff_id, "WORKLOG_CREATED", row.id, f"Worklog created for {payload.work_date}")
    db.commit()
    db.refresh(row)
    return WorklogView.model_validate(row)


@router.get("/worklogs", response_model=list[WorklogView])
def list_worklogs(staff_id: str | None = None, work_date: str | None = None, status_filter: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[WorklogView]:
    _require(user, Permission.STAFF_VIEW)
    stmt = select(StaffWorklog)
    if staff_id:
        stmt = stmt.where(StaffWorklog.staff_id == staff_id)
    if work_date:
        stmt = stmt.where(StaffWorklog.work_date == work_date)
    if status_filter:
        stmt = stmt.where(StaffWorklog.status == status_filter.strip().upper())
    return [WorklogView.model_validate(x) for x in db.scalars(stmt.order_by(StaffWorklog.work_date.desc(), StaffWorklog.created_at.desc()))]


def _transition_worklog(db: Session, request: Request, user: AuthUser, worklog_id: str, payload: WorklogTransitionRequest, target: str) -> StaffWorklog:
    _require(user, Permission.STAFF_MANAGE)
    row = db.get(StaffWorklog, worklog_id)
    if row is None:
        raise ApiError("WORKLOG_NOT_FOUND", "Worklog not found", 404)
    if row.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Worklog has changed; reload before updating", 409, {"current_version": row.version})
    allowed = {"DRAFT": {"SUBMITTED"}, "SUBMITTED": {"APPROVED"}, "APPROVED": {"LOCKED"}, "LOCKED": set()}
    if target not in allowed.get(row.status, set()):
        raise ApiError("WORKLOG_TRANSITION_INVALID", f"Cannot move worklog from {row.status} to {target}", 409)
    row.status = target
    row.version += 1
    if target in {"APPROVED", "LOCKED"}:
        row.reviewed_by_user_id = user.id
        row.reviewed_at = _utcnow()
    if target == "LOCKED":
        row.locked_at = _utcnow()
    _event(db, request, user, row.staff_id, f"WORKLOG_{target}", row.id, f"Worklog moved to {target}")
    db.commit()
    db.refresh(row)
    return row


@router.post("/worklogs/{worklog_id}/submit", response_model=WorklogView)
def submit_worklog(worklog_id: str, payload: WorklogTransitionRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorklogView:
    return WorklogView.model_validate(_transition_worklog(db, request, user, worklog_id, payload, "SUBMITTED"))


@router.post("/worklogs/{worklog_id}/approve", response_model=WorklogView)
def approve_worklog(worklog_id: str, payload: WorklogTransitionRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorklogView:
    return WorklogView.model_validate(_transition_worklog(db, request, user, worklog_id, payload, "APPROVED"))


@router.post("/worklogs/{worklog_id}/lock", response_model=WorklogView)
def lock_worklog(worklog_id: str, payload: WorklogTransitionRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> WorklogView:
    return WorklogView.model_validate(_transition_worklog(db, request, user, worklog_id, payload, "LOCKED"))


@router.get("/capacity/{staff_id}", response_model=CapacitySummary)
def capacity_summary(staff_id: str, work_date: str, standard_minutes: int = Query(default=480, ge=1, le=1440), db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> CapacitySummary:
    _require(user, Permission.STAFF_VIEW)
    _staff(db, staff_id)
    approved_leave = int(db.scalar(select(func.coalesce(func.sum(LeaveRecord.leave_minutes), 0)).where(LeaveRecord.staff_id == staff_id, LeaveRecord.leave_date == work_date, LeaveRecord.status == "APPROVED")) or 0)
    assigned = int(db.scalar(select(func.coalesce(func.sum(CapacityAssignment.assigned_minutes), 0)).where(CapacityAssignment.staff_id == staff_id, CapacityAssignment.work_date == work_date)) or 0)
    logged = int(db.scalar(select(func.coalesce(func.sum(StaffWorklog.minutes), 0)).where(StaffWorklog.staff_id == staff_id, StaffWorklog.work_date == work_date, StaffWorklog.status != "DRAFT")) or 0)
    available = max(0, standard_minutes - approved_leave)
    remaining = available - assigned
    utilization = round((assigned / available * 100), 2) if available else (100.0 if assigned else 0.0)
    return CapacitySummary(staff_id=staff_id, work_date=work_date, standard_minutes=standard_minutes, approved_leave_minutes=approved_leave, available_minutes=available, assigned_minutes=assigned, logged_minutes=logged, remaining_minutes=remaining, utilization_percent=utilization)
