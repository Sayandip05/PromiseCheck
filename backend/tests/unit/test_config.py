"""Unit tests for centralized configuration, CORS parsing, and production safety."""

import pytest

from core.config import Settings


def test_cors_origins_parsing() -> None:
    """Test parsing CORS origins from list, comma-separated string, and JSON."""
    # From comma-separated string
    s1 = Settings(CORS_ORIGINS="http://localhost:3000, https://app.example.com")
    assert s1.CORS_ORIGINS == ["http://localhost:3000", "https://app.example.com"]

    # From JSON array string
    s2 = Settings(CORS_ORIGINS='["http://localhost:3000", "https://app.example.com"]')
    assert s2.CORS_ORIGINS == ["http://localhost:3000", "https://app.example.com"]


def test_production_safety_enforcement() -> None:
    """Test that unsafe defaults are strictly forbidden in production mode."""
    # Production with default insecure secret key must fail
    with pytest.raises(ValueError, match="SESSION_SIGNING_KEY must be a secure random string"):
        Settings(
            APP_ENV="production",
            SESSION_SIGNING_KEY="dev-insecure-secret-key-change-me-32chars",
            CORS_ORIGINS=["https://app.promisecheck.com"],
        )

    # Production with wildcard CORS must fail
    with pytest.raises(ValueError, match="CORS_ORIGINS must not contain wildcard"):
        Settings(
            APP_ENV="production",
            SESSION_SIGNING_KEY="a" * 32,
            CORS_ORIGINS=["*"],
        )

    # Safe production settings must pass
    safe_settings = Settings(
        APP_ENV="production",
        SESSION_SIGNING_KEY="super-secret-production-random-token-32chars",
        CORS_ORIGINS=["https://app.promisecheck.com"],
    )
    assert safe_settings.APP_ENV == "production"
