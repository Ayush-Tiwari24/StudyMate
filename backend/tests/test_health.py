"""
Tests — Health & Readiness Probes

Tests:
1. /api/health returns component status (database, vector_backend, storage_backend).
2. /api/health/ready returns 200 and {"status": "ready"} when DB is accessible.
3. /api/health/ready returns 503 when the database is unreachable.
"""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "vector_backend" in data
    assert "storage_backend" in data
    assert "llm_provider" in data


def test_readiness_probe_success():
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_probe_database_failure(monkeypatch):
    from sqlalchemy.exc import OperationalError

    def failing_connect(*args, **kwargs):
        raise OperationalError("Connection refused", {}, None)

    from app.db.session import engine
    monkeypatch.setattr(engine, "connect", failing_connect)

    response = client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"
