from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Permission(StrEnum):
    CLIENT_VIEW = "client.view"
    CLIENT_CREATE = "client.create"
    CLIENT_UPDATE = "client.update"
    CLIENT_ARCHIVE = "client.archive"
    CLIENT_EXPORT = "client.export"

    STAFF_VIEW = "staff.view"
    STAFF_MANAGE = "staff.manage"

    ENGAGEMENT_VIEW = "engagement.view"
    ENGAGEMENT_CREATE = "engagement.create"
    ENGAGEMENT_ASSIGN = "engagement.assign"
    ENGAGEMENT_APPROVE = "engagement.approve"
    ENGAGEMENT_CLOSE = "engagement.close"
    ENGAGEMENT_REOPEN = "engagement.reopen"

    DOCUMENT_VIEW = "document.view"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_VERSION = "document.version"
    DOCUMENT_ARCHIVE = "document.archive"

    WORKING_PAPER_PREPARE = "working_paper.prepare"
    WORKING_PAPER_SUBMIT = "working_paper.submit"
    WORKING_PAPER_REVIEW = "working_paper.review"
    WORKING_PAPER_APPROVE = "working_paper.approve"
    WORKING_PAPER_LOCK = "working_paper.lock"

    AUDIT_PLAN = "audit.plan"
    AUDIT_APPROVE = "audit.approve"

    FINANCE_VIEW = "finance.view"
    FINANCE_INVOICE_CREATE = "finance.invoice.create"
    FINANCE_INVOICE_APPROVE = "finance.invoice.approve"
    FINANCE_RECEIPT_RECORD = "finance.receipt.record"

    ADMIN_USER_MANAGE = "admin.user.manage"
    ADMIN_ROLE_MANAGE = "admin.role.manage"
    ADMIN_AUDIT_LOG_VIEW = "admin.audit_log.view"


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    name: str
    permissions: frozenset[Permission]


_ALL_PERMISSIONS = frozenset(Permission)

ROLE_PERMISSIONS: dict[str, RoleDefinition] = {
    "SUPER_ADMIN": RoleDefinition("SUPER_ADMIN", _ALL_PERMISSIONS),
    "PARTNER": RoleDefinition(
        "PARTNER",
        frozenset({
            Permission.CLIENT_VIEW, Permission.CLIENT_CREATE, Permission.CLIENT_UPDATE, Permission.CLIENT_ARCHIVE, Permission.CLIENT_EXPORT,
            Permission.STAFF_VIEW,
            Permission.ENGAGEMENT_VIEW, Permission.ENGAGEMENT_CREATE, Permission.ENGAGEMENT_ASSIGN, Permission.ENGAGEMENT_APPROVE, Permission.ENGAGEMENT_CLOSE, Permission.ENGAGEMENT_REOPEN,
            Permission.DOCUMENT_VIEW, Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_VERSION, Permission.DOCUMENT_ARCHIVE,
            Permission.WORKING_PAPER_REVIEW, Permission.WORKING_PAPER_APPROVE, Permission.WORKING_PAPER_LOCK,
            Permission.AUDIT_PLAN, Permission.AUDIT_APPROVE,
            Permission.FINANCE_VIEW, Permission.FINANCE_INVOICE_APPROVE, Permission.FINANCE_RECEIPT_RECORD,
            Permission.ADMIN_AUDIT_LOG_VIEW,
        }),
    ),
    "MANAGER": RoleDefinition(
        "MANAGER",
        frozenset({
            Permission.CLIENT_VIEW, Permission.CLIENT_CREATE, Permission.CLIENT_UPDATE, Permission.STAFF_VIEW,
            Permission.ENGAGEMENT_VIEW, Permission.ENGAGEMENT_CREATE, Permission.ENGAGEMENT_ASSIGN,
            Permission.DOCUMENT_VIEW, Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_VERSION, Permission.DOCUMENT_ARCHIVE,
            Permission.WORKING_PAPER_PREPARE, Permission.WORKING_PAPER_SUBMIT, Permission.WORKING_PAPER_REVIEW,
            Permission.AUDIT_PLAN,
            Permission.FINANCE_VIEW, Permission.FINANCE_INVOICE_CREATE, Permission.FINANCE_RECEIPT_RECORD,
        }),
    ),
    "REVIEWER": RoleDefinition(
        "REVIEWER",
        frozenset({Permission.CLIENT_VIEW, Permission.ENGAGEMENT_VIEW, Permission.DOCUMENT_VIEW, Permission.WORKING_PAPER_REVIEW, Permission.AUDIT_PLAN}),
    ),
    "STAFF": RoleDefinition(
        "STAFF",
        frozenset({Permission.CLIENT_VIEW, Permission.ENGAGEMENT_VIEW, Permission.DOCUMENT_VIEW, Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_VERSION, Permission.WORKING_PAPER_PREPARE, Permission.WORKING_PAPER_SUBMIT}),
    ),
    "STUDENT": RoleDefinition(
        "STUDENT",
        frozenset({Permission.ENGAGEMENT_VIEW, Permission.DOCUMENT_VIEW, Permission.DOCUMENT_UPLOAD, Permission.WORKING_PAPER_PREPARE, Permission.WORKING_PAPER_SUBMIT}),
    ),
    "CLIENT_PORTAL_USER": RoleDefinition("CLIENT_PORTAL_USER", frozenset()),
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    definition = ROLE_PERMISSIONS.get(role)
    return definition.permissions if definition else frozenset()


def role_has_permission(role: str, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
