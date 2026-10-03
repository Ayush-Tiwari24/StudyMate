"""
Tests — Account Deletion & Data Purge

Verifies:
1. Account deletion requires a valid password confirmation.
2. Wrong password returns 401 Unauthorized.
3. Correct password wipes:
   - User SQL record
   - All associated documents and chunks
   - All ChromaDB vector embeddings
   - All stored raw PDF files
4. GET /api/auth/me/export returns complete JSON backup of user data.
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


def _create_sample_pdf(content: str = "Lecture on Graph Theory, vertex connectivity, Eulerian circuits, and Hamiltonian paths.") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _get_auth() -> dict:
    client.post("/api/auth/register", json={
        "name": "Purge User",
        "email": "purge@test.com",
        "password": "correct_password_123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "purge@test.com",
        "password": "correct_password_123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_account_deletion_with_wrong_password_rejected():
    headers = _get_auth()

    # Wrong password attempt
    resp = client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"password": "wrong_password"},
    )
    assert resp.status_code in (400, 401)
    assert "incorrect password" in resp.json()["detail"].lower()


def test_account_deletion_full_purge(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "keep_original_pdfs", True)

    headers = _get_auth()
    pdf_bytes = _create_sample_pdf("Lecture on Graph Theory, vertex connectivity, Eulerian circuits, and Hamiltonian paths.")

    # 1. Upload a document
    upload_res = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("graphs.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code in (200, 202)
    doc_id = upload_res.json()["document_id"]

    db = TestingSession()
    user = db.query(User).filter(User.email == "purge@test.com").first()
    user_id = user.id
    doc = db.query(Document).filter(Document.id == doc_id).first()
    file_path = doc.file_path
    db.close()

    # Verify storage and vectors exist
    storage = get_storage()
    assert storage.exists(file_path) is True

    collection = get_collection()
    initial_vectors = collection.get(where={"$and": [{"user_id": user_id}, {"document_id": doc_id}]})
    assert len(initial_vectors["ids"]) > 0

    # 2. Test Export Endpoint before deleting
    export_resp = client.get("/api/auth/me/export", headers=headers)
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["user"]["email"] == "purge@test.com"
    assert len(export_data["documents"]) == 1

    # 3. Delete Account with correct password
    del_resp = client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"password": "correct_password_123"},
    )
    assert del_resp.status_code == 200
    assert "deleted" in del_resp.json()["message"].lower()

    # 4. Verify all SQL records are purged
    verify_db = TestingSession()
    assert verify_db.query(User).filter(User.id == user_id).first() is None
    assert verify_db.query(Document).filter(Document.id == doc_id).first() is None
    assert verify_db.query(Chunk).filter(Chunk.document_id == doc_id).count() == 0
    verify_db.close()

    # 5. Verify Chroma vectors are deleted
    cleared_vectors = collection.get(where={"user_id": user_id})
    assert len(cleared_vectors["ids"]) == 0

    # 6. Verify storage file is removed
    assert storage.exists(file_path) is False
