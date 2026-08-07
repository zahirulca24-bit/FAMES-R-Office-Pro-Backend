from app.audit_models import AuditAcceptance, AuditIndependenceDeclaration, AuditMateriality, AuditRisk, AuditRiskProcedure
from app.audit_schemas import AcceptanceDecisionRequest, MaterialityUpsertRequest
from app.foundation.permissions import Permission, role_has_permission


def test_audit_planning_models_and_permissions_registered():
    assert AuditAcceptance.__table__.name == "audit_acceptance"
    assert AuditIndependenceDeclaration.__table__.name == "audit_independence_declarations"
    assert AuditMateriality.__table__.name == "audit_materiality"
    assert AuditRisk.__table__.name == "audit_risks"
    assert AuditRiskProcedure.__table__.name == "audit_risk_procedures"
    assert role_has_permission("PARTNER", Permission.AUDIT_PLAN) is True
    assert role_has_permission("PARTNER", Permission.AUDIT_APPROVE) is True
    assert role_has_permission("MANAGER", Permission.AUDIT_PLAN) is True
    assert role_has_permission("MANAGER", Permission.AUDIT_APPROVE) is False
    assert role_has_permission("STAFF", Permission.AUDIT_PLAN) is False


def test_acceptance_decision_and_materiality_validation_contracts():
    approved = AcceptanceDecisionRequest(expected_version=2, decision="approved")
    assert approved.decision == "APPROVED"
    materiality = MaterialityUpsertRequest(
        benchmark="Revenue",
        benchmark_amount_minor=100_000_000,
        percentage_basis_points=500,
        overall_materiality_minor=5_000_000,
        performance_materiality_minor=3_500_000,
        trivial_threshold_minor=250_000,
    )
    assert materiality.overall_materiality_minor == 5_000_000
    assert materiality.performance_materiality_minor < materiality.overall_materiality_minor
