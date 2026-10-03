"""
StudyMate RAG — Database Session

SQLAlchemy engine and session factory.
Supports:
- SQLite (local development default)
- PostgreSQL / Neon (production online stack with PgBouncer connection pooling)
"""

import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.logger import logger


def normalize_database_url(raw_url: str) -> str:
    """
    Normalise database URL:
    - Replace postgres:// or plain postgresql:// with postgresql+psycopg2://
    - Enforce sslmode=require for non-local PostgreSQL hosts (e.g. Neon, Render)
    - Strip unsupported / problematic query parameters like channel_binding or gssencmode
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

            query_params = parse_qs(parsed.query)

            # Strip params unsupported or problematic with psycopg2 in serverless Neon
            for key in ["channel_binding", "gssencmode"]:
                query_params.pop(key, None)

            if hostname not in local_hosts:
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
    # PostgreSQL / Neon pooler settings
    # Neon pooler uses PgBouncer in transaction mode.
    # Keep pool modest (5 + 5), pool_timeout=10s, and recycle before scale-to-zero (240s)
    engine_kwargs["connect_args"] = {"connect_timeout": 15}
    engine_kwargs["pool_pre_ping"] = settings.db_pool_pre_ping
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow
    engine_kwargs["pool_timeout"] = settings.db_pool_timeout
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


def log_database_startup_info() -> None:
    """Log database configuration on startup."""
    parsed = urlparse(db_url)
    hostname = parsed.hostname or "local"
    is_pooled = "-pooler" in hostname
    logger.info(
        f"Database config: host={hostname} (pooled={is_pooled}), "
        f"dialect={engine.dialect.name}, vector_backend={settings.vector_backend}, "
        f"storage_backend={settings.storage_backend}, "
        f"pool_size={settings.db_pool_size}+{settings.db_max_overflow} (timeout={settings.db_pool_timeout}s)"
    )


def execute_with_retry(fn, max_retries: int = 3, delays: tuple = (0.5, 1.0, 2.0)):
    """
    Execute a callable with exponential backoff on transient connection failures.
    Handles Neon compute wakeup delays transparently without dropping user requests.
    """
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except (OperationalError, DBAPIError) as e:
            last_err = e
            delay = delays[attempt] if attempt < len(delays) else delays[-1]
            logger.warning(
                f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay}s (Neon compute may be waking)..."
            )
            time.sleep(delay)
    raise last_err


def get_db():
    """
    FastAPI dependency that yields a database session.
    Relies on pool_pre_ping=True for connection verification without an extra SELECT 1 round trip.
    Automatically rolls back on exceptions and closes the session.
    """
    def _create_session():
        return SessionLocal()

    try:
        db = execute_with_retry(_create_session)
    except Exception as e:
        logger.error(f"Failed to acquire DB session after retries: {e}")
        raise

    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
