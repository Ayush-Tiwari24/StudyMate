"""
StudyMate RAG — Stored File Model

Stores raw file contents (e.g. PDFs) directly in the database (PostgreSQL bytea / SQLite BLOB)
when STORAGE_BACKEND=db. Kept in a dedicated table to avoid bloating the documents table.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, LargeBinary, DateTime, ForeignKey, Index,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class StoredFile(Base):
    __tablename__ = "stored_files"
    __table_args__ = (
        Index("ix_stored_files_user_id", "user_id"),
        Index("ix_stored_files_key", "key", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    key = Column(Text, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_type = Column(Text, default="application/pdf", nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=True)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="stored_files")

    def __repr__(self) -> str:
        return f"<StoredFile id={self.id} key={self.key!r} size_bytes={self.size_bytes}>"
