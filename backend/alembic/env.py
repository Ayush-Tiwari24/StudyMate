"""
Alembic Environment Configuration

Connects Alembic to our SQLAlchemy models for auto-generating and applying migrations.
Supports MIGRATION_DATABASE_URL (for direct/session connection to Supabase) with
fallback to DATABASE_URL.
"""

from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

import sys
from pathlib import Path

# Add parent directory so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import Base
from app.db.session import engine as app_engine, normalize_database_url
from app.core.config import settings
import app.models  # noqa: F401 — ensures all models are registered

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_migration_url() -> str:
    """Return normalized MIGRATION_DATABASE_URL if configured, else DATABASE_URL."""
    raw_url = settings.migration_database_url or settings.database_url
    return normalize_database_url(raw_url)


def run_migrations_offline() -> None:
    url = get_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # If a dedicated migration database URL is provided (e.g. Supabase direct session connection on port 5432),
    # use it instead of the runtime connection pooler engine.
    if settings.migration_database_url:
        mig_url = get_migration_url()
        mig_engine = create_engine(mig_url, poolclass=pool.NullPool)
        with mig_engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        mig_engine.dispose()
    else:
        with app_engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
