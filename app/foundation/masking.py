from __future__ import annotations

from collections.abc import Mapping
from typing import Any


MASKED_VALUE = "***MASKED***"

ROLE_VISIBLE_SENSITIVE_FIELDS: dict[str, frozenset[str]] = {
    "SUPER_ADMIN": frozenset({"*"}),
    "PARTNER": frozenset(
        {
            "salary",
            "staff_cost_rate",
            "engagement_profitability",
            "client_bank_information",
            "internal_risk_rating",
            "partner_comments",
        }
    ),
    "MANAGER": frozenset({"internal_risk_rating"}),
}


def mask_sensitive_fields(
    payload: Mapping[str, Any],
    *,
    role: str,
    sensitive_fields: frozenset[str],
) -> dict[str, Any]:
    """Return a copy with unauthorized sensitive values consistently masked."""
    visible = ROLE_VISIBLE_SENSITIVE_FIELDS.get(role, frozenset())
    if "*" in visible:
        return dict(payload)

    return {
        key: value if key not in sensitive_fields or key in visible else MASKED_VALUE
        for key, value in payload.items()
    }
