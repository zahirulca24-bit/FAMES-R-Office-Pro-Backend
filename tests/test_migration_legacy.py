import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrades_preexisting_create_all_style_database(tmp_path: Path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE auth_users (
            id VARCHAR(36) PRIMARY KEY,
            login_id VARCHAR(80) NOT NULL UNIQUE,
            email VARCHAR(320) UNIQUE,
            full_name VARCHAR(200) NOT NULL,
            role VARCHAR(80) NOT NULL,
            password_hash TEXT NOT NULL,
            status VARCHAR(30) NOT NULL,
            must_change_password BOOLEAN NOT NULL,
            failed_login_count INTEGER NOT NULL,
            locked_until DATETIME,
            last_login_at DATETIME,
            password_changed_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
        CREATE TABLE auth_audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36),
            login_id VARCHAR(80),
            event_type VARCHAR(80) NOT NULL,
            ip_address VARCHAR(100),
            user_agent TEXT,
            detail TEXT,
            created_at DATETIME NOT NULL
        );
        """
    )
    connection.commit()
    connection.close()

    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": f"sqlite:///{database.as_posix()}",
            "JWT_SECRET": "migration-test-secret-that-is-long-enough-2026",
            "CORS_ORIGINS": "http://localhost:5173",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    connection = sqlite3.connect(database)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(auth_users)")}
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    connection.close()
    assert "token_version" in columns
    assert revision == "20260719_01"
