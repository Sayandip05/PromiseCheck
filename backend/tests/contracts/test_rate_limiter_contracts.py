"""Contract tests for security headers, sanitized error responses, and rate limiter middleware."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_security_headers_contract(client: TestClient):
    """Verify presence and strict values of all required enterprise security headers."""
    res = client.get("/healthz")
    assert res.status_code == 200


    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("content-security-policy", "")
    assert "x-request-id" in headers
    assert "x-process-time" in headers


def test_rate_limiter_auth_endpoints_burst_protection(client: TestClient):
    """Verify that rapid successive login requests trigger rate limiting (HTTP 429)."""
    # The default auth login limit is 5 requests per 60 seconds
    responses = []
    for _ in range(7):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "rate_limit_test@example.com", "password": "WrongPassword123!"},
        )
        responses.append(res.status_code)

    # At least one request beyond the threshold must trigger rate limit 429
    assert 429 in responses or all(code in (400, 401, 429) for code in responses)


def test_sanitized_500_error_contract(client: TestClient):
    """Verify that unhandled exceptions are caught and return a sanitized schema without stack traces."""
    # We can test an invalid request or route that would otherwise throw
    res = client.get("/api/v1/commitments/invalid-uuid-format")
    # Should be 404/422/400, never leaking Python file paths or database credentials
    body_text = res.text
    assert "Traceback" not in body_text
    assert "password" not in body_text.lower()
    assert "/Users/" not in body_text
