"""
StudyMate RAG — User Model

Stores user accounts with hashed passwords and preferences.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    preferences = Column(JSON, default=dict)  # theme, model prefs, etc.
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
