from datetime import datetime, timedelta, timezone

from app.foundation.access import AccessContext, ConfidentialityLevel, evaluate_access
from app.foundation.masking import MASKED_VALUE, mask_sensitive_fields
from app.foundation.permissions import Permission


def test_access_denies_inactive_user_before_any_other_rule() -> None:
    decision = evaluate_access(
        AccessContext(
            user_id="u1",
            role="SUPER_ADMIN",
            permission=Permission.CLIENT_VIEW,
            user_is_active=False,
        )
    )
    assert decision.allowed is False
    assert decision.reason == "USER_INACTIVE"


def test_access_requires_firm_membership() -> None:
    decision = evaluate_access(
        AccessContext(
            user_id="u1",
            role="PARTNER",
            permission=Permission.CLIENT_VIEW,
            firm_member=False,
            portfolio_authorized=True,
        )
    )
    assert decision.allowed is False
    assert decision.reason == "FIRM_MEMBERSHIP_REQUIRED"


def test_partner_portfolio_grant_allows_scoped_access() -> None:
    decision = evaluate_access(
        AccessContext(
            user_id="u1",
            role="PARTNER",
            permission=Permission.CLIENT_VIEW,
            portfolio_authorized=True,
        )
    )
    assert decision.allowed is True
    assert decision.source == "PORTFOLIO"


def test_staff_without_assignment_is_denied() -> None:
    decision = evaluate_access(
        AccessContext(
            user_id="u1",
            role="STAFF",
            permission=Permission.ENGAGEMENT_VIEW,
        )
    )
    assert decision.allowed is False
    assert decision.reason == "RECORD_SCOPE_DENIED"


def test_partner_only_record_rejects_manager_even_with_assignment() -> None:
    decision = evaluate_access(
        AccessContext(
            user_id="u1",
            role="MANAGER",
            permission=Permission.CLIENT_VIEW,
            engagement_assigned=True,
            confidentiality_level=ConfidentialityLevel.PARTNER_ONLY,
        )
    )
    assert decision.allowed is False
    assert decision.reason == "PARTNER_ONLY_RECORD"


def test_restricted_record_requires_confidentiality_grant() -> None:
    denied = evaluate_access(
        AccessContext(
            user_id="u1",
            role="MANAGER",
            permission=Permission.CLIENT_VIEW,
            portfolio_authorized=True,
            confidentiality_level=ConfidentialityLevel.RESTRICTED,
        )
    )
    allowed = evaluate_access(
        AccessContext(
            user_id="u1",
            role="MANAGER",
            permission=Permission.CLIENT_VIEW,
            portfolio_authorized=True,
            confidentiality_authorized=True,
            confidentiality_level=ConfidentialityLevel.RESTRICTED,
        )
    )
    assert denied.reason == "CONFIDENTIALITY_DENIED"
    assert allowed.allowed is True


def test_delegation_is_permission_specific_and_time_bounded() -> None:
    now = datetime(2026, 8, 6, tzinfo=timezone.utc)
    context = AccessContext(
        user_id="u1",
        role="CLIENT_PORTAL_USER",
        permission=Permission.CLIENT_VIEW,
        delegation_active=True,
        delegation_permissions=frozenset({Permission.CLIENT_VIEW}),
        delegation_starts_at=now - timedelta(minutes=1),
        delegation_ends_at=now + timedelta(minutes=1),
    )
    assert evaluate_access(context, now=now).source == "DELEGATION"
    assert evaluate_access(context, now=now + timedelta(minutes=2)).reason == "ROLE_PERMISSION_DENIED"


def test_sensitive_fields_are_masked_by_backend_policy() -> None:
    payload = {
        "full_name": "Staff One",
        "salary": 50000,
        "internal_risk_rating": "HIGH",
    }
    staff_view = mask_sensitive_fields(
        payload,
        role="STAFF",
        sensitive_fields=frozenset({"salary", "internal_risk_rating"}),
    )
    manager_view = mask_sensitive_fields(
        payload,
        role="MANAGER",
        sensitive_fields=frozenset({"salary", "internal_risk_rating"}),
    )

    assert staff_view["salary"] == MASKED_VALUE
    assert staff_view["internal_risk_rating"] == MASKED_VALUE
    assert manager_view["salary"] == MASKED_VALUE
    assert manager_view["internal_risk_rating"] == "HIGH"
