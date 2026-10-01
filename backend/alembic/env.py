"""
Alembic Environment Configuration

Connects Alembic to our SQLAlchemy models for auto-generating migrations.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
from pathlib import Path

# Add parent directory so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import Base
from app.db.session import engine
from app.core.config import settings
import app.models  # noqa: F401 — ensures all models are registered

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
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
