from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LockState(StrEnum):
    OPEN = "OPEN"
    LOCKED = "LOCKED"
    REOPEN_REQUESTED = "REOPEN_REQUESTED"
    REOPENED = "REOPENED"


@dataclass(frozen=True, slots=True)
class LockContext:
    state: LockState
    actor_role: str
    reason: str | None = None
    partner_approval: bool = False


@dataclass(frozen=True, slots=True)
class LockDecision:
    allowed: bool
    reason: str
    next_state: LockState


def evaluate_lock(context: LockContext) -> LockDecision:
    if context.state not in {LockState.OPEN, LockState.REOPENED}:
        return LockDecision(False, "RECORD_NOT_LOCKABLE", context.state)
    if context.actor_role not in {"SUPER_ADMIN", "PARTNER"}:
        return LockDecision(False, "PARTNER_APPROVAL_REQUIRED", context.state)
    return LockDecision(True, "ALLOWED", LockState.LOCKED)


def evaluate_reopen_request(context: LockContext) -> LockDecision:
    if context.state != LockState.LOCKED:
        return LockDecision(False, "ONLY_LOCKED_RECORD_CAN_REQUEST_REOPEN", context.state)
    if not (context.reason and context.reason.strip()):
        return LockDecision(False, "REOPEN_REASON_REQUIRED", context.state)
    return LockDecision(True, "ALLOWED", LockState.REOPEN_REQUESTED)


def evaluate_reopen_approval(context: LockContext) -> LockDecision:
    if context.state != LockState.REOPEN_REQUESTED:
        return LockDecision(False, "REOPEN_NOT_REQUESTED", context.state)
    if context.actor_role not in {"SUPER_ADMIN", "PARTNER"} or not context.partner_approval:
        return LockDecision(False, "PARTNER_APPROVAL_REQUIRED", context.state)
    return LockDecision(True, "ALLOWED", LockState.REOPENED)
