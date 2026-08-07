from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from app.foundation.permissions import Permission, role_has_permission


class TransitionOutcome(StrEnum):
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"


@dataclass(frozen=True, slots=True)
class PolicyGate:
    code: str
    passed: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TransitionRule:
    code: str
    from_state: str
    to_state: str
    required_permission: Permission
    allowed_roles: frozenset[str] = frozenset()
    requires_reason: bool = False


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    allowed: bool
    reason: str
    failed_policy_codes: tuple[str, ...] = ()


def evaluate_policy_gates(gates: Iterable[PolicyGate]) -> tuple[bool, tuple[str, ...]]:
    failed = tuple(gate.code for gate in gates if not gate.passed)
    return (not failed, failed)


def evaluate_transition(
    *,
    current_state: str,
    actor_role: str,
    rule: TransitionRule,
    policy_gates: Iterable[PolicyGate] = (),
    action_reason: str | None = None,
) -> TransitionDecision:
    """Evaluate workflow authorization separately from professional policy gates."""
    if current_state != rule.from_state:
        return TransitionDecision(False, "INVALID_FROM_STATE")
    if not role_has_permission(actor_role, rule.required_permission):
        return TransitionDecision(False, "ROLE_PERMISSION_DENIED")
    if rule.allowed_roles and actor_role not in rule.allowed_roles:
        return TransitionDecision(False, "ROLE_NOT_ALLOWED_FOR_TRANSITION")
    if rule.requires_reason and not (action_reason and action_reason.strip()):
        return TransitionDecision(False, "ACTION_REASON_REQUIRED")

    policy_ok, failed = evaluate_policy_gates(policy_gates)
    if not policy_ok:
        return TransitionDecision(False, "POLICY_GATE_FAILED", failed)
    return TransitionDecision(True, "ALLOWED")
