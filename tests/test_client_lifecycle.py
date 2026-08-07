from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.client_lifecycle_models import ClientPortfolioOwnership, ClientRiskProfile, ClientService
from app.client_models import Client
from app.clients.lifecycle import (
    ClientStatus,
    DuplicateCandidate,
    find_duplicate_warnings,
    name_similarity,
    normalize_risk_level,
    validate_transition,
)
from app.db import SessionLocal
from app.models import AuthUser


def test_client_lifecycle_accepts_only_controlled_transitions():
    assert validate_transition(ClientStatus.PROSPECT, ClientStatus.CONFLICT_CHECK).allowed is True
    assert validate_transition(ClientStatus.CONFLICT_CHECK, ClientStatus.APPROVED).allowed is True
    assert validate_transition(ClientStatus.APPROVED, ClientStatus.ACTIVE).allowed is False
    assert validate_transition(ClientStatus.ARCHIVED, ClientStatus.ACTIVE).allowed is False
    assert validate_transition(ClientStatus.ACTIVE, ClientStatus.ACTIVE).reason == "STATUS_UNCHANGED"


def test_duplicate_warning_is_deterministic_and_advisory():
    candidates = [
        DuplicateCandidate("c1", "Acme Holdings Limited", "Acme Holdings"),
        DuplicateCandidate("c2", "Different Trading Company", None),
    ]
    warnings = find_duplicate_warnings(
        legal_name="ACME Holdings Ltd.",
        trading_name="Acme Holdings",
        candidates=candidates,
        threshold=0.75,
    )
    assert warnings
    assert warnings[0].client_id == "c1"
    assert warnings[0].score >= 0.75
    assert name_similarity("FAMES & R", "fames r") == 1.0


def test_risk_level_normalization_rejects_unknown_values():
    assert normalize_risk_level(" high ") == "HIGH"
    try:
        normalize_risk_level("extreme")
    except ValueError as exc:
        assert "unsupported client risk level" in str(exc)
    else:
        raise AssertionError("unknown risk level must be rejected")


def test_client_risk_profile_and_service_uniqueness():
    with SessionLocal() as db:
        client = Client(
            client_code="CL-TEST-005",
            legal_name="Lifecycle Test Client Limited",
            entity_type="PRIVATE_LIMITED",
        )
        db.add(client)
        db.commit()
        db.refresh(client)

        db.add(ClientRiskProfile(client_id=client.id, risk_level="HIGH", score=72))
        db.add(ClientService(client_id=client.id, service_code="AUDIT", service_name="Statutory Audit"))
        db.commit()

        db.add(ClientRiskProfile(client_id=client.id, risk_level="LOW", score=10))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("one risk profile per client must be enforced")

        db.add(ClientService(client_id=client.id, service_code="AUDIT", service_name="Duplicate Audit"))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("duplicate service activation must be blocked")


def test_partner_ownership_is_one_current_record_per_client():
    with SessionLocal() as db:
        admin = db.query(AuthUser).filter(AuthUser.login_id == "Admin@001").one()
        manager = db.query(AuthUser).filter(AuthUser.login_id == "Manager@001").one()
        client = Client(
            client_code="CL-TEST-006",
            legal_name="Portfolio Ownership Test Limited",
            entity_type="PRIVATE_LIMITED",
        )
        db.add(client)
        db.commit()
        db.refresh(client)

        db.add(
            ClientPortfolioOwnership(
                client_id=client.id,
                partner_user_id=admin.id,
                manager_user_id=manager.id,
                assigned_by_user_id=admin.id,
            )
        )
        db.commit()

        db.add(
            ClientPortfolioOwnership(
                client_id=client.id,
                partner_user_id=admin.id,
                assigned_by_user_id=admin.id,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("multiple current ownership rows must be blocked")
