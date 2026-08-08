import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.client_models import Client
from app.db import SessionLocal
from app.deps import require_password_changed
from app.engagement_models import Engagement
from app.finance_models import EngagementExpense, FinanceAction, FinanceInvoice, FinanceReceipt
from app.foundation.permissions import Permission, role_has_permission
from app.main import app
from app.models import AuthUser


def _super_admin() -> AuthUser:
    return AuthUser(
        id="test-finance-super-admin",
        login_id="finance-super-admin",
        full_name="Finance Super Admin",
        role="SUPER_ADMIN",
        password_hash="x",
        status="ACTIVE",
        must_change_password=False,
    )


def test_finance_permissions_registered():
    assert role_has_permission("PARTNER", Permission.FINANCE_INVOICE_APPROVE) is True
    assert role_has_permission("MANAGER", Permission.FINANCE_INVOICE_CREATE) is True
    assert role_has_permission("MANAGER", Permission.FINANCE_EXPENSE_RECORD) is True
    assert role_has_permission("STAFF", Permission.FINANCE_VIEW) is False


def test_invoice_receipt_expense_and_economics_reconcile():
    client_id = str(uuid.uuid4())
    engagement_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(
            Client(
                id=client_id,
                client_code=f"FRC-CLI-FIN-{uuid.uuid4().hex[:8].upper()}",
                legal_name="Finance API Test Client",
                entity_type="PRIVATE_LIMITED",
                status="ACTIVE",
            )
        )
        db.add(
            Engagement(
                id=engagement_id,
                engagement_code=f"FRC-ENG-FIN-{uuid.uuid4().hex[:8].upper()}",
                client_id=client_id,
                service_type="AUDIT",
                title="Finance API Test Engagement",
                partner_user_id="test-finance-super-admin",
                fee_currency="BDT",
                agreed_fee_minor=150000,
            )
        )
        db.commit()

    app.dependency_overrides[require_password_changed] = _super_admin
    http = TestClient(app)
    try:
        created = http.post(
            "/api/v1/finance/invoices",
            json={
                "engagement_id": engagement_id,
                "currency": "BDT",
                "subtotal_minor": 100000,
                "vat_minor": 15000,
                "tax_minor": 10000,
            },
        )
        assert created.status_code == 201, created.text
        invoice = created.json()
        assert invoice["total_minor"] == 125000
        assert invoice["status"] == "DRAFT"

        approved = http.post(
            f"/api/v1/finance/invoices/{invoice['id']}/approve",
            json={"expected_version": 1},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "APPROVED"

        receipt = http.post(
            "/api/v1/finance/receipts",
            json={
                "invoice_id": invoice["id"],
                "amount_minor": 50000,
                "received_on": str(date.today()),
                "payment_method": "BANK",
            },
        )
        assert receipt.status_code == 201, receipt.text

        overpay = http.post(
            "/api/v1/finance/receipts",
            json={
                "invoice_id": invoice["id"],
                "amount_minor": 80000,
                "received_on": str(date.today()),
                "payment_method": "BANK",
            },
        )
        assert overpay.status_code == 409
        assert overpay.json()["error"]["code"] == "RECEIPT_OVERPAYMENT"

        expense = http.post(
            "/api/v1/finance/expenses",
            json={
                "engagement_id": engagement_id,
                "category": "FIELD_VISIT",
                "amount_minor": 20000,
                "incurred_on": str(date.today()),
                "description": "Audit field visit cost",
            },
        )
        assert expense.status_code == 201, expense.text

        economics = http.get(f"/api/v1/finance/engagements/{engagement_id}/economics")
        assert economics.status_code == 200, economics.text
        body = economics.json()
        assert body["agreed_fee_minor"] == 150000
        assert body["approved_invoices_minor"] == 125000
        assert body["receipts_minor"] == 50000
        assert body["outstanding_minor"] == 75000
        assert body["expenses_minor"] == 20000
        assert body["contribution_minor"] == 105000
        assert body["collection_rate_basis_points"] == 4000
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            invoice_ids = [row[0] for row in db.query(FinanceInvoice.id).filter(FinanceInvoice.engagement_id == engagement_id).all()]
            if invoice_ids:
                db.execute(delete(FinanceReceipt).where(FinanceReceipt.invoice_id.in_(invoice_ids)))
            db.execute(delete(FinanceAction).where(FinanceAction.engagement_id == engagement_id))
            db.execute(delete(EngagementExpense).where(EngagementExpense.engagement_id == engagement_id))
            db.execute(delete(FinanceInvoice).where(FinanceInvoice.engagement_id == engagement_id))
            db.execute(delete(Engagement).where(Engagement.id == engagement_id))
            db.execute(delete(Client).where(Client.id == client_id))
            db.commit()
