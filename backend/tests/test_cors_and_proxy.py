"""
Tests — CORS and Reverse Proxy Rate Limiting
"""

from unittest.mock import MagicMock
from app.main import get_rate_limit_key


def test_rate_limit_key_authenticated_user():
    request = MagicMock()
    request.state.user = MagicMock(id=42)
    key = get_rate_limit_key(request)
    assert key == "user:42"


def test_rate_limit_key_x_forwarded_for():
    request = MagicMock()
    request.state = MagicMock(spec=[])  # No user on state
    request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    key = get_rate_limit_key(request)
    assert key == "ip:203.0.113.195"


def test_rate_limit_key_client_host_fallback():
    request = MagicMock()
    request.state = MagicMock(spec=[])
    request.headers = {}
    request.client.host = "192.168.1.50"
    key = get_rate_limit_key(request)
    assert key == "ip:192.168.1.50"
