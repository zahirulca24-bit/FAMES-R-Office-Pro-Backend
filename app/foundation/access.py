from __future__ import annotations

from dataclasses import dataclass

from app.foundation.permissions import Permission, role_has_permission


@dataclass(frozen=True, slots=True)
class AccessContext:
    user_id: str
    role: str
    permission: Permission
    user_is_active: bool = True
    firm_member: bool = True
    portfolio_authorized: bool = False
    engagement_assigned: bool = False
    confidentiality_authorized: bool = False
    delegation_active: bool = False


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: str


def evaluate_access(context: AccessContext, *, record_scope_required: bool = True) -> AccessDecision:
    """Evaluate effective access using deny-by-default semantics.

    This is the common policy boundary for future client, portfolio and engagement
    resources. Domain services must still load and validate the applicable record.
    """
    if not context.user_is_active:
        return AccessDecision(False, "USER_INACTIVE")
    if not context.firm_member:
        return AccessDecision(False, "FIRM_MEMBERSHIP_REQUIRED")
    if not role_has_permission(context.role, context.permission):
        return AccessDecision(False, "ROLE_PERMISSION_DENIED")
    if context.role == "SUPER_ADMIN" or not record_scope_required:
        return AccessDecision(True, "ALLOWED")

    scoped_access = (
        context.portfolio_authorized
        or context.engagement_assigned
        or context.confidentiality_authorized
        or context.delegation_active
    )
    if not scoped_access:
        return AccessDecision(False, "RECORD_SCOPE_DENIED")
    return AccessDecision(True, "ALLOWED")
