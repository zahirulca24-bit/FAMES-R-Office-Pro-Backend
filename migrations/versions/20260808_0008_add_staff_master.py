"""Add staff master, departments, designations and skills.

Revision ID: 20260808_0008
Revises: 20260807_0007
Create Date: 2026-08-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260808_0008"
down_revision: str | None = "20260807_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_departments_code"),
        sa.UniqueConstraint("name", name="uq_departments_name"),
    )
    op.create_index("ix_departments_code", "departments", ["code"])
    op.create_index("ix_departments_name", "departments", ["name"])
    op.create_index("ix_departments_status", "departments", ["status"])

    op.create_table(
        "designations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("rank_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_designations_code"),
        sa.UniqueConstraint("department_id", "name", name="uq_designation_department_name"),
    )
    op.create_index("ix_designations_department_id", "designations", ["department_id"])
    op.create_index("ix_designations_code", "designations", ["code"])
    op.create_index("ix_designations_name", "designations", ["name"])
    op.create_index("ix_designations_status", "designations", ["status"])

    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("staff_code", sa.String(40), nullable=False),
        sa.Column("auth_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(80), nullable=True),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("designation_id", sa.String(36), sa.ForeignKey("designations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supervisor_staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employment_type", sa.String(40), nullable=False),
        sa.Column("employment_status", sa.String(30), nullable=False),
        sa.Column("join_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("confidentiality_level", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_user_id", sa.String(36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("staff_code", name="uq_staff_profiles_staff_code"),
        sa.UniqueConstraint("auth_user_id", name="uq_staff_profiles_auth_user_id"),
    )
    for column in ("staff_code", "auth_user_id", "full_name", "email", "department_id", "designation_id", "supervisor_staff_id", "employment_type", "employment_status", "is_archived"):
        op.create_index(f"ix_staff_profiles_{column}", "staff_profiles", [column])

    op.create_table(
        "staff_skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_code", sa.String(80), nullable=False),
        sa.Column("skill_name", sa.String(160), nullable=False),
        sa.Column("proficiency_level", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("staff_id", "skill_code", name="uq_staff_skill_code"),
    )
    op.create_index("ix_staff_skills_staff_id", "staff_skills", ["staff_id"])
    op.create_index("ix_staff_skills_skill_code", "staff_skills", ["skill_code"])


def downgrade() -> None:
    op.drop_index("ix_staff_skills_skill_code", table_name="staff_skills")
    op.drop_index("ix_staff_skills_staff_id", table_name="staff_skills")
    op.drop_table("staff_skills")
    for column in reversed(("staff_code", "auth_user_id", "full_name", "email", "department_id", "designation_id", "supervisor_staff_id", "employment_type", "employment_status", "is_archived")):
        op.drop_index(f"ix_staff_profiles_{column}", table_name="staff_profiles")
    op.drop_table("staff_profiles")
    op.drop_index("ix_designations_status", table_name="designations")
    op.drop_index("ix_designations_name", table_name="designations")
    op.drop_index("ix_designations_code", table_name="designations")
    op.drop_index("ix_designations_department_id", table_name="designations")
    op.drop_table("designations")
    op.drop_index("ix_departments_status", table_name="departments")
    op.drop_index("ix_departments_name", table_name="departments")
    op.drop_index("ix_departments_code", table_name="departments")
    op.drop_table("departments")
