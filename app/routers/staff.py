from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import Department, Designation, StaffProfile, StaffSkill
from app.staff_schemas import (
    DepartmentCreateRequest,
    DepartmentView,
    DesignationCreateRequest,
    DesignationView,
    StaffCreateRequest,
    StaffDetail,
    StaffListResponse,
    StaffSkillView,
    StaffUpdateRequest,
    StaffView,
)

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _staff_code() -> str:
    return f"FRC-STF-{uuid.uuid4().hex[:10].upper()}"


def _validate_links(db: Session, department_id: str | None, designation_id: str | None, supervisor_staff_id: str | None) -> None:
    if department_id and db.get(Department, department_id) is None:
        raise ApiError("DEPARTMENT_NOT_FOUND", "Department not found", 422)
    designation = db.get(Designation, designation_id) if designation_id else None
    if designation_id and designation is None:
        raise ApiError("DESIGNATION_NOT_FOUND", "Designation not found", 422)
    if designation and department_id and designation.department_id and designation.department_id != department_id:
        raise ApiError("DESIGNATION_DEPARTMENT_MISMATCH", "Designation does not belong to department", 422)
    if supervisor_staff_id and db.get(StaffProfile, supervisor_staff_id) is None:
        raise ApiError("SUPERVISOR_NOT_FOUND", "Supervisor staff record not found", 422)


def _detail(db: Session, staff: StaffProfile) -> StaffDetail:
    skills = list(db.scalars(select(StaffSkill).where(StaffSkill.staff_id == staff.id).order_by(StaffSkill.skill_code)))
    return StaffDetail(**StaffView.model_validate(staff).model_dump(), skills=[StaffSkillView.model_validate(x) for x in skills])


def _events(db: Session, request: Request, user: AuthUser, staff: StaffProfile, event_type: str, summary: str) -> None:
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type="STAFF", resource_id=staff.id, summary=summary))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type="STAFF", resource_id=staff.id, correlation_id=cid, outcome="SUCCESS"))


@router.post("/departments", response_model=DepartmentView, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreateRequest, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> DepartmentView:
    _require(user, Permission.STAFF_MANAGE)
    item = Department(code=payload.code, name=payload.name.strip())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("DEPARTMENT_DUPLICATE", "Department code or name already exists", 409) from exc
    db.refresh(item)
    return DepartmentView.model_validate(item)


@router.post("/designations", response_model=DesignationView, status_code=status.HTTP_201_CREATED)
def create_designation(payload: DesignationCreateRequest, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> DesignationView:
    _require(user, Permission.STAFF_MANAGE)
    if payload.department_id and db.get(Department, payload.department_id) is None:
        raise ApiError("DEPARTMENT_NOT_FOUND", "Department not found", 422)
    item = Designation(code=payload.code, name=payload.name.strip(), department_id=payload.department_id, rank_order=payload.rank_order)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("DESIGNATION_DUPLICATE", "Designation code or department/name already exists", 409) from exc
    db.refresh(item)
    return DesignationView.model_validate(item)


@router.post("", response_model=StaffDetail, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> StaffDetail:
    _require(user, Permission.STAFF_MANAGE)
    _validate_links(db, payload.department_id, payload.designation_id, payload.supervisor_staff_id)
    if payload.auth_user_id and db.get(AuthUser, payload.auth_user_id) is None:
        raise ApiError("AUTH_USER_NOT_FOUND", "Linked auth user not found", 422)
    staff = StaffProfile(
        staff_code=_staff_code(), auth_user_id=payload.auth_user_id, full_name=payload.full_name.strip(),
        email=payload.email, phone=payload.phone, department_id=payload.department_id,
        designation_id=payload.designation_id, supervisor_staff_id=payload.supervisor_staff_id,
        employment_type=payload.employment_type, join_date=payload.join_date,
        confidentiality_level=payload.confidentiality_level, created_by_user_id=user.id, updated_by_user_id=user.id,
    )
    db.add(staff)
    db.flush()
    for skill in payload.skills:
        db.add(StaffSkill(staff_id=staff.id, **skill.model_dump()))
    _events(db, request, user, staff, "STAFF_CREATED", f"Staff {staff.staff_code} created")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError("STAFF_CONFLICT", "Staff auth link or skill is duplicated", 409) from exc
    db.refresh(staff)
    return _detail(db, staff)


@router.get("", response_model=StaffListResponse)
def list_staff(q: str | None = Query(default=None, max_length=200), employment_status: str | None = None, department_id: str | None = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> StaffListResponse:
    _require(user, Permission.STAFF_VIEW)
    stmt = select(StaffProfile).where(StaffProfile.is_archived.is_(False))
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(StaffProfile.full_name.ilike(needle), StaffProfile.staff_code.ilike(needle), StaffProfile.email.ilike(needle)))
    if employment_status:
        stmt = stmt.where(StaffProfile.employment_status == employment_status.strip().upper())
    if department_id:
        stmt = stmt.where(StaffProfile.department_id == department_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
    rows = list(db.scalars(stmt.order_by(StaffProfile.full_name).offset((page - 1) * page_size).limit(page_size)))
    return StaffListResponse(items=[StaffView.model_validate(x) for x in rows], page=page, page_size=page_size, total=total)


@router.get("/{staff_id}", response_model=StaffDetail)
def get_staff(staff_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> StaffDetail:
    _require(user, Permission.STAFF_VIEW)
    staff = db.get(StaffProfile, staff_id)
    if staff is None:
        raise ApiError("STAFF_NOT_FOUND", "Staff not found", 404)
    return _detail(db, staff)


@router.patch("/{staff_id}", response_model=StaffDetail)
def update_staff(staff_id: str, payload: StaffUpdateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> StaffDetail:
    _require(user, Permission.STAFF_MANAGE)
    staff = db.get(StaffProfile, staff_id)
    if staff is None:
        raise ApiError("STAFF_NOT_FOUND", "Staff not found", 404)
    if staff.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Staff record has changed; reload before updating", 409, {"current_version": staff.version})
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    _validate_links(db, updates.get("department_id", staff.department_id), updates.get("designation_id", staff.designation_id), updates.get("supervisor_staff_id", staff.supervisor_staff_id))
    if updates.get("supervisor_staff_id") == staff.id:
        raise ApiError("INVALID_SUPERVISOR", "Staff member cannot supervise themselves", 422)
    for key, value in updates.items():
        if key in {"employment_type", "employment_status", "confidentiality_level"} and isinstance(value, str):
            value = value.strip().upper()
        setattr(staff, key, value)
    staff.version += 1
    staff.updated_by_user_id = user.id
    _events(db, request, user, staff, "STAFF_UPDATED", f"Staff {staff.staff_code} updated")
    db.commit()
    db.refresh(staff)
    return _detail(db, staff)
