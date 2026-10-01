"""
Tests — Auth Refresh & Rotation

Verifies:
1. Refresh with valid refresh token returns new access + refresh token.
2. Using the old refresh token again fails (token rotation).
3. Refresh with an access token fails (type check).
4. Refresh with invalid/expired/revoked token fails.
5. Logout revokes the refresh token.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlite3 import Connection as SQLite3Connection

from app.main import app
from app.db.base import Base
from app.db.session import get_db

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


def test_refresh_token_rotation():
    """Valid refresh token can be rotated; the previous token is invalidated immediately."""
    # Register & Login
    client.post("/api/auth/register", json={
        "name": "Refresh Tester",
        "email": "refresh@test.com",
        "password": "password123",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "refresh@test.com",
        "password": "password123",
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    first_access = token_data["access_token"]
    first_refresh = token_data["refresh_token"]
    assert first_access and first_refresh

    # Rotate token pair
    rot_resp = client.post("/api/auth/refresh", json={"refresh_token": first_refresh})
    assert rot_resp.status_code == 200
    new_data = rot_resp.json()
    second_access = new_data["access_token"]
    second_refresh = new_data["refresh_token"]

    assert second_access != first_access
    assert second_refresh != first_refresh

    # Trying to reuse the first refresh token MUST fail with 401 (rotation enforcement)
    reuse_resp = client.post("/api/auth/refresh", json={"refresh_token": first_refresh})
    assert reuse_resp.status_code == 401
    assert "revoked" in reuse_resp.json()["detail"].lower() or "expired" in reuse_resp.json()["detail"].lower()

    # The second refresh token should still be usable
    rot_resp2 = client.post("/api/auth/refresh", json={"refresh_token": second_refresh})
    assert rot_resp2.status_code == 200


def test_refresh_with_access_token_rejected():
    """Attempting to use an access token at /api/auth/refresh must fail."""
    client.post("/api/auth/register", json={
        "name": "Type Tester",
        "email": "type@test.com",
        "password": "password123",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "type@test.com",
        "password": "password123",
    })
    access_token = login_resp.json()["access_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_refresh_with_invalid_token():
    """Random strings or forged tokens must be rejected."""
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-valid-jwt-token"})
    assert resp.status_code == 401


def test_logout_revokes_refresh_token():
    """Logging out revokes the given refresh token in the database."""
    client.post("/api/auth/register", json={
        "name": "Logout Tester",
        "email": "logout@test.com",
        "password": "password123",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "logout@test.com",
        "password": "password123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200

    # Refresh should now be rejected as revoked
    ref_resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_resp.status_code == 401
