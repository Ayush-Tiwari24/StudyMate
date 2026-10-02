"""
StudyMate RAG — Database Session

SQLAlchemy engine and session factory.
Supports:
- SQLite (local development default)
- PostgreSQL (production online stack with Supabase / pooler)
"""

from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger import logger


def normalize_database_url(raw_url: str) -> str:
    """
    Normalise database URL:
    - Replace postgres:// or plain postgresql:// with postgresql+psycopg2://
    - Enforce sslmode=require for non-local PostgreSQL hosts (e.g. Supabase, Render)
    """
    if not raw_url:
        return raw_url

    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # If it is PostgreSQL, check whether host is remote and enforce sslmode=require
    if url.startswith("postgresql"):
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
            local_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "postgres", "test-postgres", ""}

            if hostname not in local_hosts:
                query_params = parse_qs(parsed.query)
                if "sslmode" not in query_params:
                    query_params["sslmode"] = ["require"]
                    new_query = urlencode(query_params, doseq=True)
                    url = urlunparse((
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        new_query,
                        parsed.fragment,
                    ))
        except Exception as e:
            logger.warning(f"Could not parse database URL for SSL verification: {e}")

    return url


db_url = normalize_database_url(settings.database_url)

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
    # PostgreSQL / Supabase pooler settings
    # Small pool_size (5) + max_overflow (5) + pool_recycle (300) avoids pooler port exhaustion
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
