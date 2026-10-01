"""
StudyMate RAG — Message, MessageSource, and Feedback Models

Messages belong to a chat. Each assistant message can have sources
(citations) and optional user feedback (thumbs up/down).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_chat_created", "chat_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=True)  # e.g. "gpt-4o-mini"
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sources = relationship("MessageSource", back_populates="message", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role!r} chat={self.chat_id}>"


class MessageSource(Base):
    """A citation linking an assistant message to a specific document chunk."""
    __tablename__ = "message_sources"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    page = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    snippet = Column(Text, nullable=True)

    # Relationships
    message = relationship("Message", back_populates="sources")

    def __repr__(self) -> str:
        return f"<MessageSource id={self.id} doc={self.document_id} page={self.page}>"


class Feedback(Base):
    """Thumbs up/down feedback on an assistant message."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True)
    value = Column(Integer, nullable=False)  # 1 = 👍, -1 = 👎
    comment = Column(Text, nullable=True)

    # Relationships
    message = relationship("Message", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} value={self.value}>"
