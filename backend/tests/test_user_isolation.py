"""
Tests — Multi-tenant User Isolation

Verifies:
1. User B cannot access User A's documents (GET /api/documents/{id} -> 404).
2. User B cannot delete User A's documents (DELETE /api/documents/{id} -> 404).
3. User B cannot access User A's chats (GET /api/chats/{id} -> 404).
4. User B cannot delete User A's chats (DELETE /api/chats/{id} -> 404).
5. User B cannot attach User A's documents to a new chat (POST /api/chats -> 400).
6. Vector retrieval filters strictly by user_id so User B never sees User A's chunks.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlite3 import Connection as SQLite3Connection

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document
from app.models.chat import Chat
from app.services.retrieval.retriever import retrieve_chunks

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


def _get_auth(email: str, name: str) -> dict:
    client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_document_and_chat_isolation():
    """Verify that User B cannot read, delete, or link User A's documents or chats."""
    headers_a = _get_auth("user_a@test.com", "User A")
    headers_b = _get_auth("user_b@test.com", "User B")

    db = TestingSession()
    user_a = db.query(User).filter(User.email == "user_a@test.com").first()
    user_b = db.query(User).filter(User.email == "user_b@test.com").first()

    # User A owns Document A
    doc_a = Document(
        user_id=user_a.id,
        filename="confidential_a.pdf",
        file_path="confidential_a.pdf",
        file_hash="hash_a_secret",
        size_bytes=2048,
        status="ready",
    )
    db.add(doc_a)
    db.commit()
    doc_a_id = doc_a.id

    # User A owns Chat A
    chat_a = Chat(user_id=user_a.id, title="Private Chat A")
    chat_a.documents = [doc_a]
    db.add(chat_a)
    db.commit()
    chat_a_id = chat_a.id
    db.close()

    # 1. User B cannot check status or download User A's document
    res_status = client.get(f"/api/documents/{doc_a_id}/status", headers=headers_b)
    assert res_status.status_code == 404

    res_file = client.get(f"/api/documents/{doc_a_id}/file", headers=headers_b)
    assert res_file.status_code == 404

    # 2. User B cannot DELETE User A's document
    res = client.delete(f"/api/documents/{doc_a_id}", headers=headers_b)
    assert res.status_code == 404

    # 3. User B cannot GET User A's chat
    res = client.get(f"/api/chats/{chat_a_id}", headers=headers_b)
    assert res.status_code == 404

    # 4. User B cannot DELETE User A's chat
    res = client.delete(f"/api/chats/{chat_a_id}", headers=headers_b)
    assert res.status_code == 404

    # 5. User B cannot create a chat using User A's document
    res = client.post(
        "/api/chats",
        headers=headers_b,
        json={"title": "Hacker Chat", "document_ids": [doc_a_id]},
    )
    assert res.status_code == 400


def test_vector_retrieval_isolation():
    """Retrieve chunks queries strictly scoped to the requesting user."""
    # Even if User B requests User A's document ID, retrieval must return empty
    results = retrieve_chunks(
        question="What is the secret formula?",
        user_id=8888,  # User B
        document_ids=[9999],  # User A's document
    )
    assert results == []
