"""
StudyMate RAG — Database Session

SQLAlchemy engine and session factory.
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

from pathlib import Path

# SQLite needs connect_args for thread safety and parent directory created
connect_args = {}
db_url = settings.database_url
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

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a database session.
    Automatically closes the session when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
