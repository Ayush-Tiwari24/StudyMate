"""
StudyMate RAG — Document Model

Tracks uploaded PDFs: filename, hash (dedup), processing status,
page/chunk counts, and the chunks themselves.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Table,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ── Many-to-Many: Chats ↔ Documents ─────────────────────────────
chat_documents = Table(
    "chat_documents",
    Base.metadata,
    Column("chat_id", Integer, ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    size_bytes = Column(Integer, default=0)
    pages = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="uploaded", nullable=False)  # uploaded | processing | ready | failed
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r} status={self.status!r}>"


class Chunk(Base):
    """
    Stores chunk text + metadata for reference.
    The actual vector lives in ChromaDB, linked by `vector_id`.
    """
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_id = Column(String(100), nullable=True, index=True)  # ChromaDB ID

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} doc={self.document_id} page={self.page} idx={self.chunk_index}>"
