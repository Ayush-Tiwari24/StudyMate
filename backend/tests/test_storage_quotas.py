"""
Tests — Storage Quotas & Limits

Verifies:
1. File upload exceeding MAX_UPLOAD_MB (10 MB) is rejected with 413.
2. File upload exceeding USER_STORAGE_QUOTA_MB (50 MB) is rejected with 413:
   "You've used all your storage. Delete a document to add more."
3. File upload exceeding GLOBAL_STORAGE_CAP_MB (400 MB) is rejected with 413:
   "Uploads are paused because storage is full."
"""

import io
import pymupdf
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
import app.db.session as session_module
from app.models.user import User
from app.models.document import Document

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_quotas.db"
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


def _create_sample_pdf(text: str = "Sample") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _get_auth_headers(email: str = "quota@test.com") -> dict:
    client.post("/api/auth/register", json={
        "name": "Quota Tester",
        "email": email,
        "password": "password123",
    })
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_file_exceeding_max_upload_rejected():
    headers = _get_auth_headers("oversized@test.com")
    pdf_bytes = _create_sample_pdf()

    # Artificially set max_upload_mb to a very small size for test
    with patch.object(settings, "max_upload_mb", 1):
        # 1.5 MB payload
        large_bytes = pdf_bytes + (b"\x00" * int(1.5 * 1024 * 1024))
        res = client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": ("large.pdf", io.BytesIO(large_bytes), "application/pdf")},
        )
        assert res.status_code == 413
        assert "exceeds maximum size" in res.json()["detail"].lower()


def test_user_storage_quota_rejected_with_plain_message():
    headers = _get_auth_headers("quota_user@test.com")
    pdf_bytes = _create_sample_pdf("User quota test")

    # Set user_storage_quota_mb to 1 MB for testing
    with patch.object(settings, "user_storage_quota_mb", 1):
        # Seed an existing document that takes 900 KB
        with TestingSession() as db:
            user = db.query(User).filter(User.email == "quota_user@test.com").first()
            existing_doc = Document(
                user_id=user.id,
                filename="existing.pdf",
                file_path=f"{user.id}/existing.pdf",
                file_hash="hash12345",
                size_bytes=950 * 1024,
                status="ready",
            )
            db.add(existing_doc)
            db.commit()

        # Try to upload a 200 KB PDF (total > 1 MB)
        content_200k = pdf_bytes + (b"\x00" * (200 * 1024))
        res = client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": ("exceed.pdf", io.BytesIO(content_200k), "application/pdf")},
        )
        assert res.status_code == 413
        assert res.json()["detail"] == "You've used all your storage. Delete a document to add more."


def test_global_storage_cap_rejected_with_plain_message():
    headers = _get_auth_headers("global_user@test.com")
    pdf_bytes = _create_sample_pdf("Global cap test")

    # Mock get_database_size_bytes to return 410 MB (above 400 MB cap)
    with patch("app.api.routes.documents.get_database_size_bytes", return_value=410 * 1024 * 1024):
        res = client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert res.status_code == 413
        assert res.json()["detail"] == "Uploads are paused because storage is full."
