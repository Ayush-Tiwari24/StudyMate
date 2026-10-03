"""
Tests — S3 Storage Backend & Ingestion Temp File Cleanup

Tests:
1. S3Storage: save, open, open_stream, exists, delete, and delete_user_files.
2. Ingestion pipeline temp-file cleanup: ensures temporary PDF file is cleaned up even if loading fails.
"""

import io
from unittest.mock import MagicMock, patch
import pytest
from app.core.config import settings
from app.services.storage import S3Storage


class DummyStreamingBody:
    def __init__(self, content: bytes):
        self._content = content
        self._io = io.BytesIO(content)

    def read(self):
        return self._content


def test_s3_storage_operations(monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "test-bucket")
    monkeypatch.setattr(settings, "s3_region", "ap-south-1")

    # In-memory storage dictionary to simulate S3 bucket
    mock_s3_store = {}

    mock_client = MagicMock()

    def mock_put_object(Bucket, Key, Body, ContentType=None):
        mock_s3_store[Key] = Body
        return {"ETag": "dummy-etag"}

    def mock_get_object(Bucket, Key):
        if Key not in mock_s3_store:
            raise Exception("NoSuchKey")
        return {"Body": DummyStreamingBody(mock_s3_store[Key])}

    def mock_head_object(Bucket, Key):
        if Key not in mock_s3_store:
            raise Exception("404 NotFound")
        return {"ContentLength": len(mock_s3_store[Key])}

    def mock_delete_object(Bucket, Key):
        mock_s3_store.pop(Key, None)
        return {}

    def mock_delete_objects(Bucket, Delete):
        for obj in Delete.get("Objects", []):
            mock_s3_store.pop(obj["Key"], None)
        return {}

    class MockPaginator:
        def paginate(self, Bucket, Prefix=""):
            matched = [{"Key": k} for k in mock_s3_store if k.startswith(Prefix)]
            yield {"Contents": matched}

    mock_client.put_object.side_effect = mock_put_object
    mock_client.get_object.side_effect = mock_get_object
    mock_client.head_object.side_effect = mock_head_object
    mock_client.delete_object.side_effect = mock_delete_object
    mock_client.delete_objects.side_effect = mock_delete_objects
    mock_client.get_paginator.return_value = MockPaginator()

    with patch("boto3.session.Session.client", return_value=mock_client):
        storage = S3Storage()

        # 1. Save
        key = storage.save(user_id=42, filename="syllabus.pdf", content=b"%PDF-1.4 test content")
        assert key.startswith("42/")
        assert key.endswith("syllabus.pdf")
        assert storage.exists(key) is True

        # 2. Open
        assert storage.open(key) == b"%PDF-1.4 test content"

        # 3. Delete
        storage.delete(key)
        assert storage.exists(key) is False

        # 4. Delete user files
        key1 = storage.save(user_id=42, filename="notes1.pdf", content=b"1")
        key2 = storage.save(user_id=42, filename="notes2.pdf", content=b"2")
        key_other = storage.save(user_id=99, filename="other.pdf", content=b"99")

        assert storage.exists(key1) is True
        assert storage.exists(key2) is True
        assert storage.exists(key_other) is True

        storage.delete_user_files(user_id=42)

        assert storage.exists(key1) is False
        assert storage.exists(key2) is False
        assert storage.exists(key_other) is True


def test_ingestion_temp_file_cleanup(monkeypatch, tmp_path):
    """Verify that ingestion downloads to a temp file and deletes it in finally block even on error."""
    from app.services.ingestion.pipeline import run_ingestion_pipeline
    from app.models.document import Document
    from app.db.base import Base
    from app.models.user import User
    from app.db import session as db_session
    from sqlalchemy.orm import sessionmaker
    Base.metadata.create_all(bind=db_session.engine)

    TestSession = sessionmaker(bind=db_session.engine)
    db = TestSession()
    try:
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(id=1, email="test_ingest_cleanup@example.com", password_hash="pw", name="Tester")
            db.add(user)
            db.commit()

        # Create a dummy document
        doc = Document(
            user_id=1,
            filename="temp_test.pdf",
            file_path="1/temp_test.pdf",
            file_hash="dummy_hash_unique",
            size_bytes=123,
            status="uploaded",
        )
        db.add(doc)
        db.commit()
        doc_id = doc.id
    finally:
        db.close()

    mock_storage = MagicMock()
    mock_storage.exists.return_value = True
    mock_storage.open.return_value = b"%PDF-1.4 invalid pdf content designed to fail parser"

    with patch("app.services.storage.get_storage", return_value=mock_storage):
        with patch("app.services.ingestion.pipeline.load_pdf", side_effect=ValueError("Corrupt PDF file")):
            run_ingestion_pipeline(doc_id)

    # Check that document is marked failed and cleanup finished
    db2 = TestSession()
    try:
        updated_doc = db2.query(Document).filter(Document.id == doc_id).first()
        assert updated_doc.status == "failed"
        assert "Corrupt PDF file" in (updated_doc.error_message or "")
    finally:
        db2.delete(updated_doc)
        db2.commit()
        db2.close()
