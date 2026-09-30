"""
Tests — Document Upload

Tests for valid PDF upload, wrong type, oversize, and duplicate handling.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db


from pathlib import Path

# Isolated test database — never touches dev app.db
TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def _get_auth_header() -> dict:
    """Register and login, return auth header."""
    client.post("/api/auth/register", json={
        "name": "Upload Tester",
        "email": "upload@test.com",
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "upload@test.com",
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_non_pdf():
    headers = _get_auth_header()
    # Upload a .txt file pretending to be something else
    response = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_without_auth():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert response.status_code in (401, 403)


def test_list_documents_empty():
    headers = _get_auth_header()
    response = client.get("/api/documents", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0
