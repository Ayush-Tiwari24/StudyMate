"""
Tests — Comprehensive Document Deletion Lifecycle

Verifies:
1. Ingestion produces SQL document, chunks, Chroma vectors, and storage file.
2. DELETE /api/documents/{id} deletes SQL Document and all Chunks.
3. DELETE removes corresponding vectors from ChromaDB.
4. DELETE removes the raw file from storage backend.
5. Existing chat message citations survive with document_id set to NULL and filename falling back to 'source removed'.
"""

import io
import pymupdf
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlite3 import Connection as SQLite3Connection

from app.main import app
from app.db.base import Base
from app.db.session import get_db
import app.db.session as session_module
from app.models.user import User
from app.models.document import Document, Chunk
from app.models.chat import Chat
from app.models.message import Message, MessageSource
from app.services.storage import get_storage
from app.services.vectorstore import get_collection

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
session_module.SessionLocal = TestingSession
session_module.engine = test_engine
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_sample_pdf(content: str = "Operating Systems and Kernel Architecture.") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _get_auth() -> dict:
    client.post("/api/auth/register", json={
        "name": "Doc Delete Tester",
        "email": "docdel@test.com",
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "docdel@test.com",
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_document_deletion_lifecycle():
    """Verify complete cleanup across SQL, Chroma vectors, Storage, and citation survival."""
    headers = _get_auth()
    pdf_bytes = _create_sample_pdf("Lecture on Distributed Systems and Paxos Consensus.")

    # 1. Upload Document
    upload_res = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("paxos.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code in (200, 202)
    doc_id = upload_res.json()["document_id"]

    db = TestingSession()
    user = db.query(User).filter(User.email == "docdel@test.com").first()
    user_id = user.id
    doc = db.query(Document).filter(Document.id == doc_id).first()
    assert doc is not None
    assert doc.status == "ready"
    assert doc.progress == 100
    file_path = doc.file_path

    # Verify chunks exist in SQL
    chunks = db.query(Chunk).filter(Chunk.document_id == doc_id).all()
    assert len(chunks) > 0

    # Verify file exists in storage
    storage = get_storage()
    assert storage.exists(file_path) is True

    # Verify vectors exist in Chroma
    collection = get_collection()
    existing_vectors = collection.get(where={"$and": [{"user_id": user_id}, {"document_id": doc_id}]})
    assert len(existing_vectors["ids"]) > 0

    # 2. Create a chat session with an assistant message referencing this document
    chat = Chat(user_id=user_id, title="Paxos Study Chat")
    chat.documents = [doc]
    db.add(chat)
    db.commit()

    msg = Message(chat_id=chat.id, role="assistant", content="Paxos guarantees safety.")
    db.add(msg)
    db.commit()

    source = MessageSource(
        message_id=msg.id,
        document_id=doc.id,
        page=1,
        score=0.92,
        snippet="Paxos consensus algorithms ensure safety under asynchronous network partitions.",
    )
    db.add(source)
    db.commit()

    chat_id = chat.id
    msg_id = msg.id
    source_id = source.id
    db.close()

    # 3. Call DELETE /api/documents/{doc_id}
    del_res = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200

    # 4. Verify SQL rows are deleted
    verify_db = TestingSession()
    assert verify_db.query(Document).filter(Document.id == doc_id).first() is None
    assert verify_db.query(Chunk).filter(Chunk.document_id == doc_id).count() == 0

    # 5. Verify Chroma vectors are deleted
    cleared_vectors = collection.get(where={"$and": [{"user_id": user_id}, {"document_id": doc_id}]})
    assert len(cleared_vectors["ids"]) == 0

    # 6. Verify file is deleted from storage
    assert storage.exists(file_path) is False

    # 7. Verify existing chat message survives with source document_id = None
    chat_detail_res = client.get(f"/api/chats/{chat_id}", headers=headers)
    assert chat_detail_res.status_code == 200
    chat_data = chat_detail_res.json()
    assert len(chat_data["messages"]) == 1
    surviving_msg = chat_data["messages"][0]
    assert surviving_msg["content"] == "Paxos guarantees safety."
    assert len(surviving_msg["sources"]) == 1
    surviving_source = surviving_msg["sources"][0]
    assert surviving_source["document_id"] is None
    assert surviving_source["file"] == "source removed"

    verify_db.close()
