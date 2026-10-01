"""
StudyMate RAG — Models Package

Imports all models so Alembic and Base.metadata can discover them.
"""

from app.models.user import User
from app.models.document import Document, Chunk, chat_documents
from app.models.chat import Chat
from app.models.message import Message, MessageSource, Feedback
from app.models.refresh_token import RefreshToken

__all__ = [
    "User",
    "Document",
    "Chunk",
    "chat_documents",
    "Chat",
    "Message",
    "MessageSource",
    "Feedback",
    "RefreshToken",
]
