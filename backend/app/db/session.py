"""
StudyMate RAG — Database Session

SQLAlchemy engine and session factory.
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""

from sqlite3 import Connection as SQLite3Connection
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

from pathlib import Path

db_url = settings.database_url

# Normalise postgres:// or plain postgresql:// to postgresql+psycopg2://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine_kwargs = {
    "echo": settings.debug,
}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Parse path from sqlite:///...
    db_file_str = db_url.replace("sqlite:///", "")
    if db_file_str and not db_file_str.startswith(":memory:"):
        db_path = Path(db_file_str)
        if not db_path.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent.parent
            db_path = (backend_dir / db_path).resolve()
            db_url = f"sqlite:///{db_path.as_posix()}"
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine_kwargs["connect_args"] = connect_args
else:
    # PostgreSQL / production pool settings
    engine_kwargs["pool_pre_ping"] = settings.db_pool_pre_ping
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow
    engine_kwargs["pool_recycle"] = settings.db_pool_recycle

engine = create_engine(
    db_url,
    **engine_kwargs,
)

# Enforce foreign keys on SQLite connections
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session.
    Automatically rolls back on exceptions and closes the session.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

