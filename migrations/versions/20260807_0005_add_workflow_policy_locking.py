"""Add workflow, approval and record locking foundation.

Revision ID: 20260807_0005
Revises: 20260806_0004
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260807_0005"
down_revision: str | None = "20260806_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_column() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        _id_column(),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_workflow_definition_code_version"),
    )
    op.create_index("ix_workflow_definitions_code", "workflow_definitions", ["code"])
    op.create_index("ix_workflow_definitions_resource_type", "workflow_definitions", ["resource_type"])
    op.create_index("ix_workflow_definitions_status", "workflow_definitions", ["status"])

    op.create_table(
        "workflow_states",
        _id_column(),
        sa.Column("workflow_definition_id", sa.String(length=36), sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("terminal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("workflow_definition_id", "code", name="uq_workflow_state_code"),
    )
    op.create_index("ix_workflow_states_workflow_definition_id", "workflow_states", ["workflow_definition_id"])

    op.create_table(
        "workflow_transitions",
        _id_column(),
        sa.Column("workflow_definition_id", sa.String(length=36), sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("from_state", sa.String(length=80), nullable=False),
        sa.Column("to_state", sa.String(length=80), nullable=False),
        sa.Column("required_permission", sa.String(length=120), nullable=False),
        sa.Column("allowed_roles_json", sa.Text(), nullable=True),
        sa.Column("policy_codes_json", sa.Text(), nullable=True),
        sa.Column("requires_reason", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("workflow_definition_id", "code", name="uq_workflow_transition_code"),
    )
    op.create_index("ix_workflow_transitions_workflow_definition_id", "workflow_transitions", ["workflow_definition_id"])
    op.create_index("ix_workflow_transitions_from_state", "workflow_transitions", ["from_state"])
    op.create_index("ix_workflow_transitions_to_state", "workflow_transitions", ["to_state"])

    op.create_table(
        "workflow_instances",
        _id_column(),
        sa.Column("workflow_definition_id", sa.String(length=36), sa.ForeignKey("workflow_definitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("current_state", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resource_type", "resource_id", name="uq_workflow_instance_resource"),
    )
    for column in ("workflow_definition_id", "resource_type", "resource_id", "current_state"):
        op.create_index(f"ix_workflow_instances_{column}", "workflow_instances", [column])

    op.create_table(
        "workflow_actions",
        _id_column(),
        sa.Column("workflow_instance_id", sa.String(length=36), sa.ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("transition_code", sa.String(length=100), nullable=True),
        sa.Column("from_state", sa.String(length=80), nullable=False),
        sa.Column("to_state", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("policy_snapshot_json", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("workflow_instance_id", "actor_user_id", "action_type", "correlation_id", "created_at"):
        op.create_index(f"ix_workflow_actions_{column}", "workflow_actions", [column])

    op.create_table(
        "record_locks",
        _id_column(),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False, server_default="OPEN"),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("locked_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopen_requested_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reopen_reason", sa.String(length=1000), nullable=True),
        sa.Column("reopened_by_user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resource_type", "resource_id", name="uq_record_lock_resource"),
    )
    op.create_index("ix_record_locks_resource_type", "record_locks", ["resource_type"])
    op.create_index("ix_record_locks_resource_id", "record_locks", ["resource_id"])
    op.create_index("ix_record_locks_state", "record_locks", ["state"])


def downgrade() -> None:
    op.drop_table("record_locks")
    op.drop_table("workflow_actions")
    op.drop_table("workflow_instances")
    op.drop_table("workflow_transitions")
    op.drop_table("workflow_states")
    op.drop_table("workflow_definitions")
