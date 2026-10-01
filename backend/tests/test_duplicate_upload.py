"""
Tests — Duplicate Upload Verification

Verifies:
1. Uploading the same PDF twice by the same user returns 409 Conflict.
2. Uploading the same PDF by a different user succeeds (per-user file_hash constraint).
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


def _create_sample_pdf(title: str = "Test Lecture") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), f"{title} content for duplicate test.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _get_user_auth(name: str, email: str) -> dict:
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


def test_duplicate_upload_same_user_rejected():
    headers = _get_user_auth("User One", "user1@test.com")
    pdf_bytes = _create_sample_pdf("Duplicate Lecture")

    # First upload should succeed
    res1 = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("lecture.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res1.status_code in (200, 202), res1.text
    data1 = res1.json()
    assert data1["filename"] == "lecture.pdf"

    # Second upload with same user and identical content should return 409 Conflict
    res2 = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("lecture_renamed.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res2.status_code == 409
    detail = res2.json()["detail"].lower()
    assert "already" in detail and "uploaded" in detail


def test_duplicate_upload_different_user_allowed():
    headers_user1 = _get_user_auth("User One", "user1_diff@test.com")
    headers_user2 = _get_user_auth("User Two", "user2_diff@test.com")
    pdf_bytes = _create_sample_pdf("Shared Lecture")

    # User 1 uploads
    res1 = client.post(
        "/api/documents/upload",
        headers=headers_user1,
        files={"file": ("shared.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res1.status_code in (200, 202)

    # User 2 uploads the identical file -> should succeed because user_id differs
    res2 = client.post(
        "/api/documents/upload",
        headers=headers_user2,
        files={"file": ("shared.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res2.status_code in (200, 202)
    assert res2.json()["filename"] == "shared.pdf"
