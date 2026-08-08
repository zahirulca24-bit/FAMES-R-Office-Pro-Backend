from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_execution_models import AuditIssue
from app.client_models import Client
from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement
from app.finance_models import FinanceInvoice, FinanceReceipt
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.operations_models import BackupVerification, NotificationEvent, ProductionReadinessCheck
from app.operations_schemas import (
    BackupVerificationRequest,
    BackupVerificationView,
    ExecutiveDashboardView,
    NotificationCreateRequest,
    NotificationView,
    ProductionReadinessView,
    ReadinessCheckRequest,
    ReadinessCheckView,
)

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require(user: AuthUser, permission: Permission) -> None:
    if not role_has_permission(user.role, permission):
        raise ApiError("PERMISSION_DENIED", f"Missing permission: {permission.value}", 403)


def _event(db: Session, request: Request, user: AuthUser, event_type: str, resource_type: str, resource_id: str, detail: dict[str, object]) -> None:
    payload = json.dumps(detail, default=str)
    cid = correlation_id_from_request(request)
    db.add(ActivityEvent(actor_user_id=user.id, event_type=event_type, resource_type=resource_type, resource_id=resource_id, summary=event_type.replace("_", " ").title(), detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=event_type, resource_type=resource_type, resource_id=resource_id, correlation_id=cid, outcome="SUCCESS", detail_json=payload))


@router.get("/dashboard", response_model=ExecutiveDashboardView)
def executive_dashboard(db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ExecutiveDashboardView:
    _require(user, Permission.FINANCE_VIEW)
    active_clients = int(db.scalar(select(func.count()).select_from(Client).where(Client.status == "ACTIVE")) or 0)
    active_engagements = int(db.scalar(select(func.count()).select_from(Engagement).where(Engagement.is_archived.is_(False), Engagement.status.notin_(["CLOSED", "ARCHIVED"]))) or 0)
    open_audit_issues = int(db.scalar(select(func.count()).select_from(AuditIssue).where(AuditIssue.status != "RESOLVED")) or 0)
    approved_invoices = int(db.scalar(select(func.coalesce(func.sum(FinanceInvoice.total_minor), 0)).where(FinanceInvoice.status == "APPROVED")) or 0)
    receipts = int(db.scalar(select(func.coalesce(func.sum(FinanceReceipt.amount_minor), 0))) or 0)
    pending_notifications = int(db.scalar(select(func.count()).select_from(NotificationEvent).where(NotificationEvent.status == "PENDING")) or 0)
    return ExecutiveDashboardView(
        active_clients=active_clients,
        active_engagements=active_engagements,
        open_audit_issues=open_audit_issues,
        approved_invoices_minor=approved_invoices,
        receipts_minor=receipts,
        outstanding_minor=max(approved_invoices - receipts, 0),
        pending_notifications=pending_notifications,
    )


@router.post("/notifications", response_model=NotificationView, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> NotificationView:
    _require(user, Permission.ADMIN_AUDIT_LOG_VIEW)
    row = NotificationEvent(**payload.model_dump())
    db.add(row); db.flush()
    _event(db, request, user, "NOTIFICATION_CREATED", "NOTIFICATION", row.id, {"event_key": row.event_key, "channel": row.channel})
    db.commit(); db.refresh(row)
    return NotificationView.model_validate(row)


@router.get("/notifications", response_model=list[NotificationView])
def list_notifications(status_filter: str | None = None, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[NotificationView]:
    _require(user, Permission.ADMIN_AUDIT_LOG_VIEW)
    stmt = select(NotificationEvent)
    if status_filter:
        stmt = stmt.where(NotificationEvent.status == status_filter.strip().upper())
    rows = list(db.scalars(stmt.order_by(NotificationEvent.created_at.desc()).limit(200)))
    return [NotificationView.model_validate(row) for row in rows]


@router.post("/notifications/{notification_id}/deliver", response_model=NotificationView)
def deliver_notification(notification_id: str, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> NotificationView:
    _require(user, Permission.ADMIN_AUDIT_LOG_VIEW)
    row = db.get(NotificationEvent, notification_id)
    if row is None:
        raise ApiError("NOTIFICATION_NOT_FOUND", "Notification not found", 404)
    if row.status == "DELIVERED":
        return NotificationView.model_validate(row)
    row.status = "DELIVERED"; row.delivered_at = _now()
    _event(db, request, user, "NOTIFICATION_DELIVERED", "NOTIFICATION", row.id, {"channel": row.channel})
    db.commit(); db.refresh(row)
    return NotificationView.model_validate(row)


@router.post("/backup-verifications", response_model=BackupVerificationView, status_code=status.HTTP_201_CREATED)
def record_backup_verification(payload: BackupVerificationRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> BackupVerificationView:
    _require(user, Permission.ADMIN_AUDIT_LOG_VIEW)
    duplicate = db.scalar(select(BackupVerification.id).where(BackupVerification.backup_reference == payload.backup_reference))
    if duplicate:
        raise ApiError("BACKUP_REFERENCE_DUPLICATE", "Backup reference already verified", 409)
    row = BackupVerification(**payload.model_dump(), verified_by_user_id=user.id)
    db.add(row); db.flush()
    _event(db, request, user, "BACKUP_RESTORE_VERIFIED", "BACKUP", row.id, {"backup_status": row.backup_status, "restore_test_status": row.restore_test_status})
    db.commit(); db.refresh(row)
    return BackupVerificationView.model_validate(row)


@router.put("/readiness-checks", response_model=ReadinessCheckView)
def upsert_readiness_check(payload: ReadinessCheckRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ReadinessCheckView:
    _require(user, Permission.ADMIN_AUDIT_LOG_VIEW)
    row = db.scalar(select(ProductionReadinessCheck).where(ProductionReadinessCheck.check_key == payload.check_key))
    if row is None:
        row = ProductionReadinessCheck(check_key=payload.check_key, passed=payload.passed, evidence=payload.evidence, checked_by_user_id=user.id)
        db.add(row)
    else:
        row.passed = payload.passed; row.evidence = payload.evidence; row.checked_by_user_id = user.id; row.checked_at = _now()
    db.flush()
    _event(db, request, user, "PRODUCTION_READINESS_CHECK_UPDATED", "READINESS_CHECK", row.id, {"check_key": row.check_key, "passed": row.passed})
    db.commit(); db.refresh(row)
    return ReadinessCheckView.model_validate(row)


@router.get("/production-readiness", response_model=ProductionReadinessView)
def production_readiness(db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ProductionReadinessView:
    _require(user, Permission.ADMIN_AUDIT_LOG_VIEW)
    checks = list(db.scalars(select(ProductionReadinessCheck).order_by(ProductionReadinessCheck.check_key)))
    latest_backup = db.scalar(select(BackupVerification).order_by(BackupVerification.verified_at.desc()).limit(1))
    backup_ok = latest_backup is not None and latest_backup.backup_status == "SUCCESS" and latest_backup.restore_test_status == "SUCCESS"
    blockers = [row.check_key for row in checks if not row.passed]
    if not backup_ok:
        blockers.append("BACKUP_RESTORE")
    passed = sum(1 for row in checks if row.passed)
    return ProductionReadinessView(ready=bool(checks) and passed == len(checks) and backup_ok, checks_total=len(checks), checks_passed=passed, backup_restore_verified=backup_ok, blockers=blockers)
