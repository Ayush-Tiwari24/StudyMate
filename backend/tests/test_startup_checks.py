"""
Tests — Startup Security Guards in Production
"""

import asyncio
import pytest
from app.core.config import settings
from app.main import lifespan, app


def test_production_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret", "change-me-to-a-random-string")
    monkeypatch.setattr(settings, "database_url", "postgresql://user:pass@host:5432/db")

    async def _run():
        async with lifespan(app):
            pass

    with pytest.raises(RuntimeError, match="JWT_SECRET must be at least 32 characters"):
        asyncio.run(_run())


def test_production_rejects_short_jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret", "short-secret")
    monkeypatch.setattr(settings, "database_url", "postgresql://user:pass@host:5432/db")

    async def _run():
        async with lifespan(app):
            pass

    with pytest.raises(RuntimeError, match="JWT_SECRET must be at least 32 characters"):
        asyncio.run(_run())


def test_production_rejects_sqlite(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "jwt_secret", "a" * 32)
    monkeypatch.setattr(settings, "database_url", "sqlite:///./data/app.db")

    async def _run():
        async with lifespan(app):
            pass

    with pytest.raises(RuntimeError, match="DATABASE_URL cannot be SQLite in production"):
        asyncio.run(_run())
