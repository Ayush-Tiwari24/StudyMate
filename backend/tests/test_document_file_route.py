"""
Tests — Document File Download & Usage Endpoints

Verifies:
1. GET /api/documents/{id}/file streams original PDF with Content-Type, Content-Length, and inline Disposition.
2. GET /api/documents/{id}/file enforces user tenancy (cannot download another user's document).
3. GET /api/documents/usage returns valid storage quota, used bytes, and percentage.
"""

import io
import pymupdf
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
import app.db.session as session_module
from app.models.user import User
from app.models.document import Document
from app.services.storage import get_storage

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_file_route.db"
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


def _create_sample_pdf(text: str = "Test PDF Content") -> bytes:
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


def test_download_document_file_success():
    headers = _get_auth_headers("downloader@test.com", "Downloader")
    pdf_bytes = _create_sample_pdf("Lecture Notes for Algorithms")

    # Upload document
    upload_res = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("algorithms.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code in (200, 202)
    doc_id = upload_res.json()["document_id"]

    # Download document file
    file_res = client.get(f"/api/documents/{doc_id}/file", headers=headers)
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "application/pdf"
    assert "algorithms.pdf" in file_res.headers.get("content-disposition", "")
    assert int(file_res.headers.get("content-length", 0)) == len(pdf_bytes)
    assert file_res.content == pdf_bytes


def test_download_document_tenancy_isolation():
    user1_headers = _get_auth_headers("user1@test.com", "User One")
    user2_headers = _get_auth_headers("user2@test.com", "User Two")

    pdf_bytes = _create_sample_pdf("User 1 Secret Notes")
    upload_res = client.post(
        "/api/documents/upload",
        headers=user1_headers,
        files={"file": ("secret.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = upload_res.json()["document_id"]

    # User 2 tries to download User 1's file
    res = client.get(f"/api/documents/{doc_id}/file", headers=user2_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_storage_usage_endpoints():
    headers = _get_auth_headers("quota_user@test.com", "Quota User")
    pdf_bytes = _create_sample_pdf("Quota Test Document")

    # Initial usage should be 0
    usage_res1 = client.get("/api/documents/usage", headers=headers)
    assert usage_res1.status_code == 200
    data1 = usage_res1.json()
    assert data1["used_bytes"] == 0
    assert data1["quota_mb"] == 50
    assert data1["percent_used"] == 0.0

    # Upload document
    upload_res = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("quota_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code in (200, 202)

    # Usage after upload
    usage_res2 = client.get("/api/documents/usage", headers=headers)
    assert usage_res2.status_code == 200
    data2 = usage_res2.json()
    assert data2["used_bytes"] == len(pdf_bytes)
    assert data2["used_mb"] >= 0.0
    assert data2["quota_bytes"] == 50 * 1024 * 1024

    # GET /api/documents list should also include storage fields
    list_res = client.get("/api/documents", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["storage_used_bytes"] == len(pdf_bytes)
    assert list_data["storage_quota_mb"] == 50

    # GET /api/auth/me should also include storage fields
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["storage_used_bytes"] == len(pdf_bytes)
    assert me_data["storage_quota_bytes"] == 50 * 1024 * 1024
