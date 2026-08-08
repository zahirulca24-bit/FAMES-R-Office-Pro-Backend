from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvoiceCreateRequest(BaseModel):
    engagement_id: str
    currency: str = Field(default="BDT", min_length=3, max_length=3)
    subtotal_minor: int = Field(gt=0)
    vat_minor: int = Field(default=0, ge=0)
    tax_minor: int = Field(default=0, ge=0)
    due_date: date | None = None
    note: str | None = Field(default=None, max_length=4000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class InvoiceDecisionRequest(BaseModel):
    expected_version: int = Field(ge=1)


class ReceiptCreateRequest(BaseModel):
    invoice_id: str
    amount_minor: int = Field(gt=0)
    received_on: date
    payment_method: str = Field(default="BANK", max_length=40)
    reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=4000)

    @field_validator("payment_method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        return value.strip().upper()


class ExpenseCreateRequest(BaseModel):
    engagement_id: str
    category: str = Field(min_length=2, max_length=80)
    amount_minor: int = Field(gt=0)
    incurred_on: date
    description: str = Field(min_length=2, max_length=500)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.strip().upper()


class InvoiceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    invoice_number: str
    engagement_id: str
    currency: str
    subtotal_minor: int
    vat_minor: int
    tax_minor: int
    total_minor: int
    due_date: date | None
    status: str
    version: int
    note: str | None
    approved_by_user_id: str | None
    approved_at: datetime | None
    created_at: datetime


class ReceiptView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    receipt_number: str
    invoice_id: str
    amount_minor: int
    received_on: date
    payment_method: str
    reference: str | None
    note: str | None
    created_at: datetime


class ExpenseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    engagement_id: str
    category: str
    amount_minor: int
    incurred_on: date
    description: str
    status: str
    created_at: datetime


class EngagementEconomicsView(BaseModel):
    engagement_id: str
    currency: str
    agreed_fee_minor: int
    approved_invoices_minor: int
    receipts_minor: int
    outstanding_minor: int
    expenses_minor: int
    contribution_minor: int
    collection_rate_basis_points: int
