"""
Tests — Settings & Preferences Hardening

Verifies:
1. Strict Pydantic validation rejects invalid values (top_k, temperature, theme).
2. extra="forbid" rejects unknown/unexpected fields with 422.
3. GET /api/settings returns merged defaults for new users (no nulls).
4. Updating settings successfully saves and merges.
5. Asking a question without top_k respects the user's saved top_k preference.
"""

from unittest.mock import patch
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


def _get_auth(email: str = "settings_user@test.com") -> dict:
    client.post("/api/auth/register", json={
        "name": "Settings Tester",
        "email": email,
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_settings_returns_defaults():
    """Brand new user gets default configuration values, never null."""
    headers = _get_auth("defaults@test.com")
    resp = client.get("/api/settings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["theme"] in ("light", "night", "dark", "system")
    assert data["top_k"] == 5
    assert data["temperature"] == 0.1
    assert data["llm_provider"] in ("groq", "openai", "ollama")
    assert data["font_scale"] == "medium"
    assert data["show_chunks"] is False


def test_put_settings_validation_errors():
    """Invalid fields or values out of bounds must be rejected with 422."""
    headers = _get_auth("validation@test.com")

    # top_k out of bounds (> 10)
    res = client.put("/api/settings", headers=headers, json={"top_k": 99})
    assert res.status_code == 422

    # top_k out of bounds (< 1)
    res = client.put("/api/settings", headers=headers, json={"top_k": 0})
    assert res.status_code == 422

    # temperature out of bounds (> 1.0)
    res = client.put("/api/settings", headers=headers, json={"temperature": 2.5})
    assert res.status_code == 422

    # temperature out of bounds (< 0.0)
    res = client.put("/api/settings", headers=headers, json={"temperature": -0.2})
    assert res.status_code == 422

    # unknown theme
    res = client.put("/api/settings", headers=headers, json={"theme": "neon-green"})
    assert res.status_code == 422

    # extra unknown attribute (extra="forbid")
    res = client.put("/api/settings", headers=headers, json={"unrecognized_key": "injected"})
    assert res.status_code == 422


def test_put_settings_success():
    """Valid settings update merges and persists cleanly."""
    headers = _get_auth("valid_update@test.com")

    payload = {
        "theme": "night",
        "top_k": 8,
        "temperature": 0.4,
        "font_scale": "large",
        "show_chunks": True,
    }
    put_resp = client.put("/api/settings", headers=headers, json=payload)
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["theme"] == "night"
    assert data["top_k"] == 8
    assert data["temperature"] == 0.4
    assert data["font_scale"] == "large"
    assert data["show_chunks"] is True

    # Re-fetch via GET to verify persistence
    get_resp = client.get("/api/settings", headers=headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["top_k"] == 8
    assert get_data["theme"] == "night"
    assert get_data["font_scale"] == "large"


def test_pipeline_respects_user_top_k():
    """When top_k is not supplied in question, pipeline receives user's saved top_k."""
    headers = _get_auth("pipeline_topk@test.com")

    # Update user's top_k to 8
    client.put("/api/settings", headers=headers, json={"top_k": 8})

    # Create a document for the user first
    db = TestingSession()
    user = db.query(User).filter(User.email == "pipeline_topk@test.com").first()
    doc = Document(
        user_id=user.id,
        filename="lecture.pdf",
        file_path="lecture.pdf",
        file_hash="test_hash_settings",
        size_bytes=1024,
        status="ready",
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id
    db.close()

    # Create a chat session with the document
    chat_resp = client.post(
        "/api/chats",
        headers=headers,
        json={"title": "Settings Test Chat", "document_ids": [doc_id]},
    )
    assert chat_resp.status_code in (200, 201)
    chat_id = chat_resp.json()["id"]

    # We mock rag_query to inspect the arguments passed to it
    with patch("app.services.generation.rag_chain.rag_query") as mock_rag_query:
        async def fake_rag_stream(**kwargs):
            yield {"type": "token", "text": "Hello"}

        mock_rag_query.side_effect = fake_rag_stream

        # User asks without explicit top_k in request body
        ask_resp = client.post(
            f"/api/chats/{chat_id}/ask",
            headers=headers,
            json={"question": "What is normalization?", "document_ids": [1]},
        )
        assert ask_resp.status_code == 200
        assert mock_rag_query.called
        call_kwargs = mock_rag_query.call_args.kwargs
        assert call_kwargs.get("top_k") == 8
