from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_password_changed
from app.engagement_models import Engagement, EngagementTeamMember
from app.finance_models import EngagementExpense, FinanceAction, FinanceInvoice, FinanceReceipt
from app.finance_schemas import (
    EngagementEconomicsView,
    ExpenseCreateRequest,
    ExpenseView,
    InvoiceCreateRequest,
    InvoiceDecisionRequest,
    InvoiceView,
    ReceiptCreateRequest,
    ReceiptView,
)
from app.foundation.http import ApiError, correlation_id_from_request
from app.foundation.permissions import Permission, role_has_permission
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.staff_models import StaffProfile

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


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
        raise ApiError("FINANCE_ENGAGEMENT_ACCESS_DENIED", "You do not have access to this engagement", 403)
    return engagement


def _number(prefix: str) -> str:
    return f"FRC-{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _event(db: Session, request: Request, user: AuthUser, engagement_id: str, resource_type: str, resource_id: str, action: str, detail: dict[str, object]) -> None:
    payload = json.dumps(detail, default=str)
    db.add(FinanceAction(engagement_id=engagement_id, resource_type=resource_type, resource_id=resource_id, action=action, actor_user_id=user.id, detail_json=payload))
    db.add(ActivityEvent(actor_user_id=user.id, event_type=action, resource_type=resource_type, resource_id=resource_id, summary=action.replace("_", " ").title(), detail_json=payload))
    db.add(AuditEvent(actor_user_id=user.id, event_type=action, resource_type=resource_type, resource_id=resource_id, correlation_id=correlation_id_from_request(request), outcome="SUCCESS", detail_json=payload))


@router.post("/invoices", response_model=InvoiceView, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> InvoiceView:
    engagement = _accessible(db, user, payload.engagement_id, Permission.FINANCE_INVOICE_CREATE)
    if payload.currency != engagement.fee_currency:
        raise ApiError("FINANCE_CURRENCY_MISMATCH", "Invoice currency must match engagement fee currency", 422)
    total = payload.subtotal_minor + payload.vat_minor + payload.tax_minor
    row = FinanceInvoice(
        invoice_number=_number("INV"), engagement_id=engagement.id, currency=payload.currency,
        subtotal_minor=payload.subtotal_minor, vat_minor=payload.vat_minor, tax_minor=payload.tax_minor,
        total_minor=total, due_date=payload.due_date, note=payload.note, created_by_user_id=user.id,
    )
    db.add(row); db.flush()
    _event(db, request, user, engagement.id, "FINANCE_INVOICE", row.id, "INVOICE_CREATED", {"invoice_number": row.invoice_number, "total_minor": total})
    db.commit(); db.refresh(row)
    return InvoiceView.model_validate(row)


@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceView)
def approve_invoice(invoice_id: str, payload: InvoiceDecisionRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> InvoiceView:
    _require(user, Permission.FINANCE_INVOICE_APPROVE)
    row = db.get(FinanceInvoice, invoice_id)
    if row is None:
        raise ApiError("INVOICE_NOT_FOUND", "Invoice not found", 404)
    _accessible(db, user, row.engagement_id, Permission.FINANCE_INVOICE_APPROVE)
    if row.version != payload.expected_version:
        raise ApiError("VERSION_CONFLICT", "Invoice has changed; reload before approval", 409, {"current_version": row.version})
    if row.status != "DRAFT":
        raise ApiError("INVOICE_INVALID_STATE", "Only draft invoices can be approved", 409)
    row.status = "APPROVED"; row.version += 1; row.approved_by_user_id = user.id; row.approved_at = _now()
    _event(db, request, user, row.engagement_id, "FINANCE_INVOICE", row.id, "INVOICE_APPROVED", {"total_minor": row.total_minor})
    db.commit(); db.refresh(row)
    return InvoiceView.model_validate(row)


@router.post("/receipts", response_model=ReceiptView, status_code=status.HTTP_201_CREATED)
def record_receipt(payload: ReceiptCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ReceiptView:
    _require(user, Permission.FINANCE_RECEIPT_RECORD)
    invoice = db.get(FinanceInvoice, payload.invoice_id)
    if invoice is None:
        raise ApiError("INVOICE_NOT_FOUND", "Invoice not found", 404)
    _accessible(db, user, invoice.engagement_id, Permission.FINANCE_RECEIPT_RECORD)
    if invoice.status != "APPROVED":
        raise ApiError("RECEIPT_REQUIRES_APPROVED_INVOICE", "Receipts can only be recorded against approved invoices", 409)
    received = int(db.scalar(select(func.coalesce(func.sum(FinanceReceipt.amount_minor), 0)).where(FinanceReceipt.invoice_id == invoice.id)) or 0)
    if received + payload.amount_minor > invoice.total_minor:
        raise ApiError("RECEIPT_OVERPAYMENT", "Receipt would exceed the invoice balance", 409, {"outstanding_minor": invoice.total_minor - received})
    row = FinanceReceipt(receipt_number=_number("RCT"), invoice_id=invoice.id, amount_minor=payload.amount_minor, received_on=payload.received_on, payment_method=payload.payment_method, reference=payload.reference, note=payload.note, recorded_by_user_id=user.id)
    db.add(row); db.flush()
    _event(db, request, user, invoice.engagement_id, "FINANCE_RECEIPT", row.id, "RECEIPT_RECORDED", {"invoice_id": invoice.id, "amount_minor": row.amount_minor})
    db.commit(); db.refresh(row)
    return ReceiptView.model_validate(row)


@router.post("/expenses", response_model=ExpenseView, status_code=status.HTTP_201_CREATED)
def record_expense(payload: ExpenseCreateRequest, request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> ExpenseView:
    engagement = _accessible(db, user, payload.engagement_id, Permission.FINANCE_EXPENSE_RECORD)
    row = EngagementExpense(engagement_id=engagement.id, category=payload.category, amount_minor=payload.amount_minor, incurred_on=payload.incurred_on, description=payload.description, recorded_by_user_id=user.id)
    db.add(row); db.flush()
    _event(db, request, user, engagement.id, "ENGAGEMENT_EXPENSE", row.id, "EXPENSE_RECORDED", {"category": row.category, "amount_minor": row.amount_minor})
    db.commit(); db.refresh(row)
    return ExpenseView.model_validate(row)


@router.get("/engagements/{engagement_id}/economics", response_model=EngagementEconomicsView)
def engagement_economics(engagement_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> EngagementEconomicsView:
    engagement = _accessible(db, user, engagement_id, Permission.FINANCE_VIEW)
    invoiced = int(db.scalar(select(func.coalesce(func.sum(FinanceInvoice.total_minor), 0)).where(FinanceInvoice.engagement_id == engagement.id, FinanceInvoice.status == "APPROVED")) or 0)
    receipts = int(db.scalar(select(func.coalesce(func.sum(FinanceReceipt.amount_minor), 0)).join(FinanceInvoice, FinanceInvoice.id == FinanceReceipt.invoice_id).where(FinanceInvoice.engagement_id == engagement.id)) or 0)
    expenses = int(db.scalar(select(func.coalesce(func.sum(EngagementExpense.amount_minor), 0)).where(EngagementExpense.engagement_id == engagement.id, EngagementExpense.status == "RECORDED")) or 0)
    agreed = int(engagement.agreed_fee_minor or 0)
    rate = int((receipts * 10000) / invoiced) if invoiced > 0 else 0
    return EngagementEconomicsView(
        engagement_id=engagement.id, currency=engagement.fee_currency, agreed_fee_minor=agreed,
        approved_invoices_minor=invoiced, receipts_minor=receipts, outstanding_minor=invoiced - receipts,
        expenses_minor=expenses, contribution_minor=invoiced - expenses, collection_rate_basis_points=rate,
    )


@router.get("/invoices/{invoice_id}/receipts", response_model=list[ReceiptView])
def invoice_receipts(invoice_id: str, db: Session = Depends(get_db), user: AuthUser = Depends(require_password_changed)) -> list[ReceiptView]:
    invoice = db.get(FinanceInvoice, invoice_id)
    if invoice is None:
        raise ApiError("INVOICE_NOT_FOUND", "Invoice not found", 404)
    _accessible(db, user, invoice.engagement_id, Permission.FINANCE_VIEW)
    rows = list(db.scalars(select(FinanceReceipt).where(FinanceReceipt.invoice_id == invoice.id).order_by(FinanceReceipt.received_on, FinanceReceipt.created_at)))
    return [ReceiptView.model_validate(row) for row in rows]
