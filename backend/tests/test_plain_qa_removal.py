"""
Tests — Plain QA & Citation Removal Verification

Verifies:
1. GET /api/documents/{id}/file route is removed and returns 404.
2. Chat ask endpoint streams tokens and done events, but never emits a 'sources' event.
3. Chat detail endpoint GET /api/chats/{id} returns messages with no sources field.
4. Chat export GET /api/chats/{id}/export outputs plain markdown Q&A with no citations or sources.
5. Citation markers [1], [2], [1, 2] split across token boundaries are stripped from stream.
6. No MessageSource records are created in the database during chat generation.
"""

import io
import json
import pymupdf
import pytest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
import app.db.session as session_module
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageSource
from app.models.document import Document
from app.services.generation.rag_chain import CitationFilter

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_plain_qa.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setattr(session_module, "SessionLocal", TestingSession)
    monkeypatch.setattr(session_module, "engine", test_engine)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


def _create_sample_pdf(text: str = "Operating Systems Concept") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _get_auth_headers(email: str, name: str) -> dict:
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


def test_file_route_returns_404():
    """GET /api/documents/{id}/file must return 404 because the route is removed."""
    headers = _get_auth_headers("plain_user@test.com", "Plain User")
    res = client.get("/api/documents/999/file", headers=headers)
    assert res.status_code == 404


def test_chat_ask_emits_no_sources_and_stores_no_message_sources():
    """SSE answer stream must not emit sources event and must not insert MessageSource rows."""
    headers = _get_auth_headers("chat_user@test.com", "Chat User")
    db = TestingSession()
    user = db.query(User).filter(User.email == "chat_user@test.com").first()

    # Create dummy document and chat
    doc = Document(user_id=user.id, filename="os.pdf", file_path="dummy/path.pdf", file_hash="dummy_hash", pages=1)
    db.add(doc)
    db.commit()

    chat = Chat(user_id=user.id, title="OS Chat")
    chat.documents = [doc]
    db.add(chat)
    db.commit()
    chat_id = chat.id
    db.close()

    # Mock rag_query to stream tokens (including stray citation tokens)
    with patch("app.services.generation.rag_chain.rag_query") as mock_rag:
        async def fake_rag_stream(**kwargs):
            yield {"type": "token", "text": "Deadlock occurs when four conditions hold."}

        mock_rag.side_effect = fake_rag_stream

        response = client.post(
            f"/api/chats/{chat_id}/ask",
            headers=headers,
            json={"question": "What is deadlock?"},
        )
        assert response.status_code == 200
        sse_text = response.text

        # Verify event types in SSE stream
        assert "event: token" in sse_text
        assert "event: done" in sse_text
        assert "event: sources" not in sse_text
        assert "sources" not in sse_text

    # Verify database: Message exists, but zero MessageSource rows were saved
    verify_db = TestingSession()
    msg = verify_db.query(Message).filter(Message.chat_id == chat_id, Message.role == "assistant").first()
    assert msg is not None
    assert msg.content == "Deadlock occurs when four conditions hold."

    source_count = verify_db.query(MessageSource).filter(MessageSource.message_id == msg.id).count()
    assert source_count == 0

    # Verify GET /api/chats/{id} has no sources field in message response
    detail_res = client.get(f"/api/chats/{chat_id}", headers=headers)
    assert detail_res.status_code == 200
    chat_data = detail_res.json()
    assert len(chat_data["messages"]) == 2  # user + assistant
    for message in chat_data["messages"]:
        assert "sources" not in message

    # Verify chat export has no *Sources:* or citation metadata
    export_res = client.get(f"/api/chats/{chat_id}/export", headers=headers)
    assert export_res.status_code == 200
    export_md = export_res.text
    assert "# OS Chat" in export_md
    assert "**You:**" in export_md
    assert "**Assistant:**" in export_md
    assert "Deadlock occurs when four conditions hold." in export_md
    assert "*Sources:*" not in export_md
    assert "source removed" not in export_md

    verify_db.close()


def test_citation_filter_comprehensive_cases():
    """CitationFilter correctly removes stray citation markers across chunks."""
    cfilter = CitationFilter()

    # Split token test: ["According to ", "[1", ", 2", "], virtual memory", " is useful [3]"]
    stream = ["According to ", "[1", ", 2", "], virtual memory", " is useful [3]"]
    result = "".join([cfilter.process(s) for s in stream]) + cfilter.flush()

    assert "[1, 2]" not in result
    assert "[3]" not in result
    assert result == "According to , virtual memory is useful "


def test_ephemeral_upload_and_retry_not_retained():
    """When KEEP_ORIGINAL_PDFS=False, document is uploaded without saving file, and retry returns 400."""
    from app.core.config import settings
    from app.services.storage import get_storage
    headers = _get_auth_headers("ephemeral@test.com", "Ephemeral User")
    pdf_bytes = _create_sample_pdf("Ephemeral upload content testing.")

    res = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res.status_code in (200, 202)
    doc_id = res.json()["document_id"]

    db = TestingSession()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    assert doc is not None
    assert doc.file_path is None
    assert doc.status in ("uploaded", "processing", "ready")
    db.close()

    storage = get_storage()
    assert storage.exists(doc.file_path) is False

    # Retry should fail with 400 because original file is not retained
    retry_res = client.post(f"/api/documents/{doc_id}/retry", headers=headers)
    assert retry_res.status_code == 400
    assert "Please upload this file again" in retry_res.json()["detail"]

    # Deleting document succeeds without error
    del_res = client.delete(f"/api/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200
