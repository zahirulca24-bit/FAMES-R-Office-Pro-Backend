from app.foundation.locking import LockContext, LockState, evaluate_lock, evaluate_reopen_approval, evaluate_reopen_request
from app.foundation.permissions import Permission
from app.foundation.workflow import PolicyGate, TransitionRule, evaluate_transition
from app.workflow_models import RecordLock, WorkflowAction, WorkflowDefinition, WorkflowInstance, WorkflowState, WorkflowTransition


def test_transition_rejects_wrong_start_state():
    rule = TransitionRule(
        code="SUBMIT_FOR_PARTNER",
        from_state="MANAGER_REVIEW",
        to_state="PARTNER_REVIEW",
        required_permission=Permission.ENGAGEMENT_APPROVE,
        allowed_roles=frozenset({"PARTNER"}),
    )
    decision = evaluate_transition(current_state="DRAFT", actor_role="PARTNER", rule=rule)
    assert decision.allowed is False
    assert decision.reason == "INVALID_FROM_STATE"


def test_transition_enforces_role_and_policy_separately():
    rule = TransitionRule(
        code="FINALIZE",
        from_state="PARTNER_REVIEW",
        to_state="LOCKED",
        required_permission=Permission.ENGAGEMENT_CLOSE,
        allowed_roles=frozenset({"PARTNER", "SUPER_ADMIN"}),
    )
    denied_role = evaluate_transition(current_state="PARTNER_REVIEW", actor_role="MANAGER", rule=rule)
    assert denied_role.allowed is False
    assert denied_role.reason == "ROLE_PERMISSION_DENIED"

    denied_policy = evaluate_transition(
        current_state="PARTNER_REVIEW",
        actor_role="PARTNER",
        rule=rule,
        policy_gates=(
            PolicyGate("ALL_HIGH_RISK_ISSUES_RESOLVED", False),
            PolicyGate("WORKING_PAPERS_REVIEWED", True),
        ),
    )
    assert denied_policy.allowed is False
    assert denied_policy.reason == "POLICY_GATE_FAILED"
    assert denied_policy.failed_policy_codes == ("ALL_HIGH_RISK_ISSUES_RESOLVED",)


def test_rejection_reason_can_be_mandatory():
    rule = TransitionRule(
        code="REJECT_TO_PREPARER",
        from_state="UNDER_REVIEW",
        to_state="DRAFT",
        required_permission=Permission.WORKING_PAPER_REVIEW,
        allowed_roles=frozenset({"REVIEWER", "MANAGER", "PARTNER"}),
        requires_reason=True,
    )
    decision = evaluate_transition(current_state="UNDER_REVIEW", actor_role="REVIEWER", rule=rule)
    assert decision.allowed is False
    assert decision.reason == "ACTION_REASON_REQUIRED"


def test_lock_requires_partner_and_reopen_requires_reason_and_approval():
    denied = evaluate_lock(LockContext(state=LockState.OPEN, actor_role="MANAGER"))
    assert denied.allowed is False
    assert denied.reason == "PARTNER_APPROVAL_REQUIRED"

    locked = evaluate_lock(LockContext(state=LockState.OPEN, actor_role="PARTNER"))
    assert locked.allowed is True
    assert locked.next_state == LockState.LOCKED

    no_reason = evaluate_reopen_request(LockContext(state=LockState.LOCKED, actor_role="MANAGER"))
    assert no_reason.allowed is False
    assert no_reason.reason == "REOPEN_REASON_REQUIRED"

    requested = evaluate_reopen_request(
        LockContext(state=LockState.LOCKED, actor_role="MANAGER", reason="Client supplied corrected evidence")
    )
    assert requested.allowed is True
    assert requested.next_state == LockState.REOPEN_REQUESTED

    denied_reopen = evaluate_reopen_approval(
        LockContext(state=LockState.REOPEN_REQUESTED, actor_role="MANAGER", partner_approval=True)
    )
    assert denied_reopen.allowed is False

    reopened = evaluate_reopen_approval(
        LockContext(state=LockState.REOPEN_REQUESTED, actor_role="PARTNER", partner_approval=True)
    )
    assert reopened.allowed is True
    assert reopened.next_state == LockState.REOPENED


def test_workflow_tables_are_registered():
    assert WorkflowDefinition.__tablename__ == "workflow_definitions"
    assert WorkflowState.__tablename__ == "workflow_states"
    assert WorkflowTransition.__tablename__ == "workflow_transitions"
    assert WorkflowInstance.__tablename__ == "workflow_instances"
    assert WorkflowAction.__tablename__ == "workflow_actions"
    assert RecordLock.__tablename__ == "record_locks"
