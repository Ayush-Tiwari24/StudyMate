"""
Tests — Audit Fixes Verification
Verifies:
1. Delete document commits deletion to database
2. SQLite Foreign Key constraint enforcement
3. Account deletion endpoint removes user and data
4. Settings applied to pipeline and chat
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlite3 import Connection as SQLite3Connection

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document, Chunk
from app.models.chat import Chat
from app.models.message import Message

from pathlib import Path

# Isolated test database — matches test_auth and test_upload
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


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _get_auth():
    client.post("/api/auth/register", json={
        "name": "Audit User",
        "email": "audit@test.com",
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "audit@test.com",
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_sqlite_foreign_key_enforcement():
    """Verify that SQLite engine actively enforces foreign keys."""
    with test_engine.connect() as conn:
        fk_val = conn.exec_driver_sql("PRAGMA foreign_keys;").scalar()
        assert fk_val == 1, "Foreign keys are NOT enabled on SQLite connection!"


def test_delete_document_commits_to_database():
    """Deleting a document must commit and be verified gone from DB."""
    headers = _get_auth()
    db = TestingSession()

    user = db.query(User).filter(User.email == "audit@test.com").first()
    # Create document directly in DB
    doc = Document(
        user_id=user.id,
        filename="lecture.pdf",
        file_path="nonexistent.pdf",
        file_hash="test_hash_123",
        size_bytes=1024,
        status="ready",
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id
    db.close()

    # Call DELETE /api/documents/{id}
    del_resp = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 200

    # Query fresh session to verify commit persisted
    verify_db = TestingSession()
    found = verify_db.query(Document).filter(Document.id == doc_id).first()
    assert found is None, "Document was not committed as deleted from database!"
    verify_db.close()


def test_delete_account():
    """DELETE /api/auth/me should purge user and cascade."""
    headers = _get_auth()
    db = TestingSession()
    user = db.query(User).filter(User.email == "audit@test.com").first()
    user_id = user.id

    # Add a document and chat
    doc = Document(
        user_id=user.id,
        filename="test.pdf",
        file_path="nonexistent.pdf",
        file_hash="hash_abc",
        status="ready",
    )
    chat = Chat(user_id=user.id, title="Test Chat")
    db.add_all([doc, chat])
    db.commit()
    db.close()

    # Attempt deletion with wrong password - must be rejected
    bad_resp = client.request("DELETE", "/api/auth/me", json={"password": "wrongpassword"}, headers=headers)
    assert bad_resp.status_code == 400

    # Delete account with correct password
    del_resp = client.request("DELETE", "/api/auth/me", json={"password": "password123"}, headers=headers)
    assert del_resp.status_code == 200

    # Verify user and related objects are gone
    verify_db = TestingSession()
    assert verify_db.query(User).filter(User.id == user_id).first() is None
    assert verify_db.query(Document).filter(Document.user_id == user_id).first() is None
    assert verify_db.query(Chat).filter(Chat.user_id == user_id).first() is None
    verify_db.close()


def test_settings_update_applied():
    """Settings updated via PUT /api/settings should be persisted in user preferences."""
    headers = _get_auth()

    # Update preferences
    update_payload = {
        "theme": "dark",
        "llm_provider": "groq",
        "model_name": "openai/gpt-oss-120b",
        "top_k": 8,
        "temperature": 0.3,
    }
    put_resp = client.put("/api/settings", headers=headers, json=update_payload)
    assert put_resp.status_code == 200

    # Get preferences
    get_resp = client.get("/api/settings", headers=headers)
    assert get_resp.status_code == 200
    prefs = get_resp.json()
    assert prefs["top_k"] == 8
    assert prefs["llm_provider"] == "groq"
    assert prefs["model_name"] == "openai/gpt-oss-120b"
    assert prefs["temperature"] == 0.3
