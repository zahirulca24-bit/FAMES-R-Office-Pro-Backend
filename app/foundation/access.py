from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from app.foundation.permissions import Permission, role_has_permission


class ConfidentialityLevel(StrEnum):
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    PARTNER_ONLY = "PARTNER_ONLY"


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
    confidentiality_level: ConfidentialityLevel = ConfidentialityLevel.INTERNAL
    delegation_active: bool = False
    delegation_permissions: frozenset[Permission] = frozenset()
    delegation_starts_at: datetime | None = None
    delegation_ends_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: str
    source: str | None = None


def _delegation_is_effective(context: AccessContext, now: datetime) -> bool:
    if not context.delegation_active or context.permission not in context.delegation_permissions:
        return False
    if context.delegation_starts_at and now < context.delegation_starts_at:
        return False
    if context.delegation_ends_at and now >= context.delegation_ends_at:
        return False
    return True


def evaluate_access(
    context: AccessContext,
    *,
    record_scope_required: bool = True,
    now: datetime | None = None,
) -> AccessDecision:
    """Evaluate role, membership, record scope and confidentiality.

    Access is deny-by-default. A delegation can grant only an explicitly listed
    permission and never bypasses active-user, firm-membership or confidentiality
    checks.
    """
    now = now or datetime.now(timezone.utc)

    if not context.user_is_active:
        return AccessDecision(False, "USER_INACTIVE")
    if not context.firm_member:
        return AccessDecision(False, "FIRM_MEMBERSHIP_REQUIRED")

    role_allowed = role_has_permission(context.role, context.permission)
    delegation_allowed = _delegation_is_effective(context, now)
    if not role_allowed and not delegation_allowed:
        return AccessDecision(False, "ROLE_PERMISSION_DENIED")

    if context.confidentiality_level == ConfidentialityLevel.PARTNER_ONLY and context.role not in {
        "SUPER_ADMIN",
        "PARTNER",
    }:
        return AccessDecision(False, "PARTNER_ONLY_RECORD")
    if (
        context.confidentiality_level == ConfidentialityLevel.RESTRICTED
        and context.role != "SUPER_ADMIN"
        and not context.confidentiality_authorized
    ):
        return AccessDecision(False, "CONFIDENTIALITY_DENIED")

    if context.role == "SUPER_ADMIN" or not record_scope_required:
        return AccessDecision(True, "ALLOWED", "ROLE")

    if context.portfolio_authorized:
        return AccessDecision(True, "ALLOWED", "PORTFOLIO")
    if context.engagement_assigned:
        return AccessDecision(True, "ALLOWED", "ENGAGEMENT")
    if context.confidentiality_authorized:
        return AccessDecision(True, "ALLOWED", "CONFIDENTIALITY_GRANT")
    if delegation_allowed:
        return AccessDecision(True, "ALLOWED", "DELEGATION")

    return AccessDecision(False, "RECORD_SCOPE_DENIED")
