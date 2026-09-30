"""
StudyMate RAG — Declarative Base

Shared base for all SQLAlchemy models.
Import this in every model file: `from app.db.base import Base`
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass
