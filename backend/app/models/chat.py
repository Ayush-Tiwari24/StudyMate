"""
StudyMate RAG — Chat Model

A chat groups messages around a topic / set of documents.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.document import chat_documents  # many-to-many table


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")
    documents = relationship(
        "Document",
        secondary=chat_documents,
        backref="chats",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Chat id={self.id} title={self.title!r}>"
