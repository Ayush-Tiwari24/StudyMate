"""
Tests — Neon Connection Normalisation & Retry Handling

Verifies:
1. normalize_database_url converts postgresql:// to postgresql+psycopg2://.
2. normalize_database_url enforces sslmode=require on non-local Neon hosts.
3. normalize_database_url strips problematic channel_binding and gssencmode params.
4. execute_with_retry successfully retries transient connection errors (Neon compute cold-start).
5. execute_with_retry raises exception after exceeding max_retries.
"""

import pytest
from sqlalchemy.exc import OperationalError

from app.db.session import normalize_database_url, execute_with_retry


def test_normalize_database_url_neon():
    # Neon pooled connection string with channel_binding
    neon_raw = (
        "postgresql://user:pass@ep-xyz-pooler.ap-southeast-1.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    normalized = normalize_database_url(neon_raw)

    assert normalized.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in normalized
    assert "channel_binding" not in normalized


def test_normalize_database_url_adds_sslmode_for_remote():
    raw = "postgresql://user:pass@ep-cool-lake-12345.ap-southeast-1.aws.neon.tech/neondb"
    normalized = normalize_database_url(raw)

    assert normalized.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in normalized


def test_normalize_database_url_local_sqlite_untouched():
    sqlite_url = "sqlite:///./data/app.db"
    assert normalize_database_url(sqlite_url) == sqlite_url


def test_execute_with_retry_succeeds_first_time():
    calls = 0

    def work():
        nonlocal calls
        calls += 1
        return "success"

    result = execute_with_retry(work, max_retries=3, delays=(0.01, 0.01))
    assert result == "success"
    assert calls == 1


def test_execute_with_retry_recovers_after_transient_error():
    attempts = 0

    def waking_db():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise OperationalError("Connection refused: Neon compute waking up", {}, None)
        return "connected"

    result = execute_with_retry(waking_db, max_retries=3, delays=(0.01, 0.01))
    assert result == "connected"
    assert attempts == 2


def test_execute_with_retry_exhausted_raises():
    def always_down():
        raise OperationalError("Database completely down", {}, None)

    with pytest.raises(OperationalError) as exc_info:
        execute_with_retry(always_down, max_retries=2, delays=(0.01, 0.01))

    assert "Database completely down" in str(exc_info.value)
