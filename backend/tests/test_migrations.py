"""
Tests — Alembic Migrations Verification

Verifies:
1. 'alembic upgrade head' successfully applies baseline migration creating all 9 tables.
2. 'alembic downgrade base' rolls back cleanly.
3. 'alembic upgrade head' re-applies cleanly without errors.
"""

from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command
import app.db.session as session_module


def test_alembic_migration_roundtrip(tmp_path):
    """Run upgrade -> downgrade -> upgrade cycle programmatically."""
    mig_db_file = tmp_path / "migration_test.db"
    mig_db_url = f"sqlite:///{mig_db_file.as_posix()}"
    mig_engine = create_engine(mig_db_url, connect_args={"check_same_thread": False})

    # Save original engine and point session engine to migration test DB
    orig_engine = session_module.engine
    session_module.engine = mig_engine

    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", mig_db_url)

    expected_tables = {
        "users",
        "documents",
        "chunks",
        "chats",
        "chat_documents",
        "messages",
        "message_sources",
        "feedback",
        "refresh_tokens",
    }

    try:
        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")
        inspector = inspect(mig_engine)
        tables = set(inspector.get_table_names())
        for expected in expected_tables:
            assert expected in tables, f"Expected table '{expected}' not found after upgrade head"

        # 2. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        inspector = inspect(mig_engine)
        downgraded_tables = set(inspector.get_table_names())
        for expected in expected_tables:
            assert expected not in downgraded_tables, f"Table '{expected}' still exists after downgrade base"

        # 3. Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        inspector = inspect(mig_engine)
        reupgraded_tables = set(inspector.get_table_names())
        for expected in expected_tables:
            assert expected in reupgraded_tables, f"Table '{expected}' not found after re-upgrade head"

    finally:
        mig_engine.dispose()
        session_module.engine = orig_engine
