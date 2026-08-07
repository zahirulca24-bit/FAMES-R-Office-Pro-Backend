from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ClientStatus(StrEnum):
    PROSPECT = "PROSPECT"
    CONFLICT_CHECK = "CONFLICT_CHECK"
    APPROVED = "APPROVED"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    ARCHIVED = "ARCHIVED"


_ALLOWED_TRANSITIONS: dict[ClientStatus, frozenset[ClientStatus]] = {
    ClientStatus.PROSPECT: frozenset({ClientStatus.CONFLICT_CHECK, ClientStatus.ARCHIVED}),
    ClientStatus.CONFLICT_CHECK: frozenset({ClientStatus.APPROVED, ClientStatus.ARCHIVED}),
    ClientStatus.APPROVED: frozenset({ClientStatus.ONBOARDING, ClientStatus.ARCHIVED}),
    ClientStatus.ONBOARDING: frozenset({ClientStatus.ACTIVE, ClientStatus.SUSPENDED, ClientStatus.ARCHIVED}),
    ClientStatus.ACTIVE: frozenset({ClientStatus.SUSPENDED, ClientStatus.TERMINATED}),
    ClientStatus.SUSPENDED: frozenset({ClientStatus.ACTIVE, ClientStatus.TERMINATED}),
    ClientStatus.TERMINATED: frozenset({ClientStatus.ARCHIVED}),
    ClientStatus.ARCHIVED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class LifecycleDecision:
    allowed: bool
    reason: str


def validate_transition(current: str, target: str) -> LifecycleDecision:
    try:
        current_status = ClientStatus(current)
        target_status = ClientStatus(target)
    except ValueError:
        return LifecycleDecision(False, "UNKNOWN_CLIENT_STATUS")

    if current_status == target_status:
        return LifecycleDecision(False, "STATUS_UNCHANGED")
    if target_status not in _ALLOWED_TRANSITIONS[current_status]:
        return LifecycleDecision(False, "INVALID_CLIENT_STATUS_TRANSITION")
    return LifecycleDecision(True, "ALLOWED")


def normalize_duplicate_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def name_similarity(left: str | None, right: str | None) -> float:
    a = normalize_duplicate_text(left)
    b = normalize_duplicate_text(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    # Deterministic Dice coefficient over character bigrams. It is intentionally
    # advisory only; identifiers remain the hard duplicate-prevention boundary.
    def bigrams(text: str) -> list[str]:
        return [text[index : index + 2] for index in range(max(len(text) - 1, 1))]

    a_pairs = bigrams(a)
    b_pairs = bigrams(b)
    available = list(b_pairs)
    matches = 0
    for pair in a_pairs:
        if pair in available:
            matches += 1
            available.remove(pair)
    return (2.0 * matches) / (len(a_pairs) + len(b_pairs))


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    client_id: str
    legal_name: str
    trading_name: str | None = None


@dataclass(frozen=True, slots=True)
class DuplicateWarning:
    client_id: str
    score: float
    field: str


def find_duplicate_warnings(
    *,
    legal_name: str,
    trading_name: str | None,
    candidates: Iterable[DuplicateCandidate],
    threshold: float = 0.86,
) -> list[DuplicateWarning]:
    if threshold <= 0 or threshold > 1:
        raise ValueError("threshold must be within (0, 1]")

    warnings: list[DuplicateWarning] = []
    for candidate in candidates:
        comparisons = (
            ("legal_name", name_similarity(legal_name, candidate.legal_name)),
            ("trading_name", name_similarity(trading_name, candidate.trading_name)),
            ("cross_name", name_similarity(legal_name, candidate.trading_name)),
        )
        field, score = max(comparisons, key=lambda item: item[1])
        if score >= threshold:
            warnings.append(DuplicateWarning(candidate.client_id, round(score, 4), field))
    return sorted(warnings, key=lambda item: (-item.score, item.client_id))


VALID_RISK_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH", "VERY_HIGH"})


def normalize_risk_level(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VALID_RISK_LEVELS:
        raise ValueError("unsupported client risk level")
    return normalized
