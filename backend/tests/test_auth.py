"""
Tests — Authentication

Tests for register, login, protected routes, and invalid credentials.
"""

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
    """Create fresh tables for each test in isolated in-memory DB."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def test_register_success():
    response = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data


def test_register_duplicate_email():
    # Register first
    client.post("/api/auth/register", json={
        "name": "User 1",
        "email": "dup@example.com",
        "password": "password123",
    })
    # Try duplicate
    response = client.post("/api/auth/register", json={
        "name": "User 2",
        "email": "dup@example.com",
        "password": "password456",
    })
    assert response.status_code == 409


def test_login_success():
    # Register first
    client.post("/api/auth/register", json={
        "name": "Login User",
        "email": "login@example.com",
        "password": "password123",
    })
    # Login
    response = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    client.post("/api/auth/register", json={
        "name": "User",
        "email": "wrong@example.com",
        "password": "correct_password",
    })
    response = client.post("/api/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrong_password",
    })
    assert response.status_code == 401


def test_protected_route_without_token():
    response = client.get("/api/auth/me")
    assert response.status_code in (401, 403)  # Missing Authorization header


def test_me_with_valid_token():
    # Register + Login
    client.post("/api/auth/register", json={
        "name": "Me User",
        "email": "me@example.com",
        "password": "password123",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "me@example.com",
        "password": "password123",
    })
    token = login_resp.json()["access_token"]

    # Access protected route
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
