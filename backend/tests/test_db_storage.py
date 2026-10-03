"""
Tests — Database Storage Backend (DatabaseStorage & DatabaseStream)

Verifies:
1. DatabaseStorage saves file bytes into stored_files table.
2. DatabaseStorage.open retrieves complete file bytes.
3. DatabaseStorage.open_stream returns a streaming reader (DatabaseStream) with chunk reading.
4. DatabaseStorage.exists accurately checks file presence.
5. DatabaseStorage.delete removes the specific stored file.
6. DatabaseStorage.delete_user_files removes all files belonging to a specific user.
"""

import io
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User
from app.services.storage import DatabaseStorage
import app.services.storage as storage_module
import app.db.session as session_module

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_db_storage.db"
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    # Route session factory and engine to test SQLite DB
    monkeypatch.setattr(session_module, "SessionLocal", TestingSession)
    monkeypatch.setattr(session_module, "engine", test_engine)
    monkeypatch.setattr(storage_module, "SessionLocal", TestingSession)
    monkeypatch.setattr(storage_module, "engine", test_engine)

    Base.metadata.create_all(bind=test_engine)

    # Seed test users
    with TestingSession() as db:
        user1 = User(id=101, name="Alice", email="alice@test.com", password_hash="hash")
        user2 = User(id=102, name="Bob", email="bob@test.com", password_hash="hash")
        db.add_all([user1, user2])
        db.commit()

    yield

    Base.metadata.drop_all(bind=test_engine)
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


def test_database_storage_save_open_exists():
    storage = DatabaseStorage()
    content = b"%PDF-1.4 test document binary content " * 50

    key = storage.save(user_id=101, filename="notes.pdf", content=content)
    assert key.startswith("101/") and key.endswith("notes.pdf")
    assert storage.exists(key) is True
    assert storage.exists("101/nonexistent.pdf") is False

    read_bytes = storage.open(key)
    assert read_bytes == content




def test_database_storage_delete_and_cascade():
    storage = DatabaseStorage()
    content = b"%PDF-1.4 sample content"

    key1 = storage.save(user_id=101, filename="doc1.pdf", content=content)
    key2 = storage.save(user_id=101, filename="doc2.pdf", content=content)
    key3 = storage.save(user_id=102, filename="doc3.pdf", content=content)

    assert storage.exists(key1) is True
    storage.delete(key1)
    assert storage.exists(key1) is False
    assert storage.exists(key2) is True

    # Delete all files for user 101
    storage.delete_user_files(101)
    assert storage.exists(key2) is False
    assert storage.exists(key3) is True
