from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.client_lifecycle_models import (  # noqa: F401
    ClientArchiveEvent,
    ClientConflictCheck,
    ClientPortfolioOwnership,
    ClientRiskProfile,
    ClientService,
)
from app.client_models import (  # noqa: F401
    Client,
    ClientAddress,
    ClientContact,
    ClientDirector,
    ClientIdentifier,
    ClientRelationship,
    ClientShareholder,
    ClientStatusHistory,
)
from app.config import get_settings
from app.db import Base
from app.models import AuthAuditLog, AuthUser  # noqa: F401
from app.staff_models import Department, Designation, StaffProfile, StaffSkill  # noqa: F401
from app.workforce_models import AttendanceRecord, CapacityAssignment, LeaveRecord, StaffWorklog  # noqa: F401
from app.workflow_models import (  # noqa: F401
    RecordLock,
    WorkflowAction,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowState,
    WorkflowTransition,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
