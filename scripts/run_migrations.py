from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_migrations")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "alembic.ini"

    if not config_path.is_file():
        logger.error("Alembic config not found: %s", config_path)
        return 1

    logger.info("Starting database migration using %s", config_path)

    try:
        alembic_config = Config(str(config_path))
        alembic_config.set_main_option("script_location", str(project_root / "migrations"))
        command.upgrade(alembic_config, "head")
    except Exception:
        logger.exception("Database migration failed")
        return 1

    logger.info("Database migration completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
