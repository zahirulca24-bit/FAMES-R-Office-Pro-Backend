from app.audit_execution_models import AuditCompletion, AuditCompletionAction, AuditIssue, AuditRequisition, AuditTest
from app.audit_execution_schemas import AuditIssueCreateRequest, FinalizationReadinessView, RequisitionStatusRequest
from app.foundation.permissions import Permission, role_has_permission


def test_audit_execution_models_registered():
    assert AuditRequisition.__table__.name == "audit_requisitions"
    assert AuditTest.__table__.name == "audit_tests"
    assert AuditIssue.__table__.name == "audit_issues"
    assert AuditCompletion.__table__.name == "audit_completion"
    assert AuditCompletionAction.__table__.name == "audit_completion_actions"


def test_audit_execution_permissions_are_separated_from_finalization():
    assert role_has_permission("STAFF", Permission.AUDIT_EXECUTE) is True
    assert role_has_permission("STAFF", Permission.AUDIT_FINALIZE) is False
    assert role_has_permission("MANAGER", Permission.AUDIT_EXECUTE) is True
    assert role_has_permission("MANAGER", Permission.AUDIT_FINALIZE) is False
    assert role_has_permission("PARTNER", Permission.AUDIT_FINALIZE) is True
    assert role_has_permission("SUPER_ADMIN", Permission.AUDIT_FINALIZE) is True


def test_execution_schema_controls():
    status = RequisitionStatusRequest(expected_version=1, status="received", response_note="Received from client")
    assert status.status == "RECEIVED"
    issue = AuditIssueCreateRequest(issue_code="iss-001", title="Revenue cutoff", severity="high", description="Cutoff exception")
    assert issue.issue_code == "ISS-001"
    assert issue.severity == "HIGH"
    readiness = FinalizationReadinessView(
        engagement_id="eng-1",
        ready=False,
        planning_ready=True,
        completion_checklist_ready=True,
        open_requisitions=0,
        incomplete_tests=0,
        open_high_risk_issues=1,
        open_other_issues=0,
        unlocked_working_papers=0,
        significant_risks_without_procedure=0,
    )
    assert readiness.ready is False
    assert readiness.open_high_risk_issues == 1
