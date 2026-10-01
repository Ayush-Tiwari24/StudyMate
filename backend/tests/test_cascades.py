"""
Tests — Foreign Key Enforcement & Cascading Deletions

Verifies:
1. Deleting a chat cascades to all its messages and message sources.
2. Deleting a user cascades to all documents, chunks, chats, refresh tokens, and feedback.
3. Foreign key constraints are actively enforced (PRAGMA foreign_keys=ON on SQLite raises IntegrityError).
"""

from datetime import datetime, timezone
import pytest
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlite3 import Connection as SQLite3Connection

from app.db.base import Base
from app.models.user import User
from app.models.document import Document, Chunk
from app.models.chat import Chat
from app.models.message import Message, MessageSource, Feedback
from app.models.refresh_token import RefreshToken

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_chat_delete_cascades_messages_and_sources():
    """Deleting a chat removes all associated messages and citation sources."""
    db = TestingSession()

    user = User(name="Cascade User", email="cascade@test.com", password_hash="hashed")
    db.add(user)
    db.commit()

    chat = Chat(user_id=user.id, title="Test Chat")
    db.add(chat)
    db.commit()

    msg = Message(chat_id=chat.id, role="assistant", content="Test response")
    db.add(msg)
    db.commit()

    src = MessageSource(message_id=msg.id, page=1, score=0.95, snippet="Sample text")
    db.add(src)
    db.commit()

    msg_id = msg.id
    src_id = src.id

    # Verify rows exist
    assert db.query(Message).filter(Message.id == msg_id).first() is not None
    assert db.query(MessageSource).filter(MessageSource.id == src_id).first() is not None

    # Delete Chat
    db.delete(chat)
    db.commit()

    # Verify cascade deletion
    assert db.query(Message).filter(Message.id == msg_id).first() is None
    assert db.query(MessageSource).filter(MessageSource.id == src_id).first() is None
    db.close()


def test_user_delete_cascades_all_entities():
    """Deleting a user removes all their documents, chunks, chats, feedback, and refresh tokens."""
    db = TestingSession()

    user = User(name="Root User", email="root@test.com", password_hash="hashed")
    db.add(user)
    db.commit()

    # Document & Chunk
    doc = Document(
        user_id=user.id,
        filename="root.pdf",
        file_path="root.pdf",
        file_hash="root_hash_123",
        size_bytes=1000,
        status="ready",
    )
    db.add(doc)
    db.commit()

    chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        content="Root content",
        page=1,
    )
    db.add(chunk)
    db.commit()

    # Chat & Message & Feedback
    chat = Chat(user_id=user.id, title="Root Chat")
    db.add(chat)
    db.commit()

    msg = Message(chat_id=chat.id, role="user", content="Hello root")
    db.add(msg)
    db.commit()

    fb = Feedback(message_id=msg.id, value=1)
    db.add(fb)
    db.commit()

    # Refresh token
    rt = RefreshToken(
        user_id=user.id,
        token_hash="fake_token_hash",
        expires_at=datetime.now(timezone.utc),
    )
    db.add(rt)
    db.commit()

    doc_id = doc.id
    chunk_id = chunk.id
    chat_id = chat.id
    msg_id = msg.id
    fb_id = fb.id
    rt_id = rt.id

    # Delete User directly from SQL
    db.delete(user)
    db.commit()

    # Verify everything cascaded
    assert db.query(Document).filter(Document.id == doc_id).first() is None
    assert db.query(Chunk).filter(Chunk.id == chunk_id).first() is None
    assert db.query(Chat).filter(Chat.id == chat_id).first() is None
    assert db.query(Message).filter(Message.id == msg_id).first() is None
    assert db.query(Feedback).filter(Feedback.id == fb_id).first() is None
    assert db.query(RefreshToken).filter(RefreshToken.id == rt_id).first() is None
    db.close()


def test_sqlite_foreign_key_violation_raises():
    """Inserting a document with invalid foreign key user_id raises IntegrityError."""
    db = TestingSession()

    # Non-existent user_id = 999999
    bad_doc = Document(
        user_id=999999,
        filename="invalid.pdf",
        file_path="invalid.pdf",
        file_hash="bad_hash",
        size_bytes=1000,
        status="ready",
    )
    db.add(bad_doc)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
    db.close()
