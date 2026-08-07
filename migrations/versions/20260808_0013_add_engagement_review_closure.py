"""Add engagement review and closure history.

Revision ID: 20260808_0013
Revises: 20260808_0012
"""

from alembic import op
import sqlalchemy as sa

revision = "20260808_0013"
down_revision = "20260808_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engagement_review_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("engagement_id", sa.String(36), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=False),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("blocker_snapshot_json", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_engagement_review_actions_engagement_id", "engagement_review_actions", ["engagement_id"])
    op.create_index("ix_engagement_review_actions_action_type", "engagement_review_actions", ["action_type"])
    op.create_index("ix_engagement_review_actions_actor_user_id", "engagement_review_actions", ["actor_user_id"])
    op.create_index("ix_engagement_review_actions_correlation_id", "engagement_review_actions", ["correlation_id"])
    op.create_index("ix_engagement_review_actions_created_at", "engagement_review_actions", ["created_at"])


def downgrade() -> None:
    op.drop_table("engagement_review_actions")
