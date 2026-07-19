"""Tests for Settings validators in app/config.py."""

import pytest

from app.config import Settings


def test_production_rejects_short_admin_api_key():
    """In production, ADMIN_API_KEY must be at least 32 characters."""
    with pytest.raises(ValueError, match="32 characters"):
        Settings(
            environment="production",
            admin_api_key="short",
            jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
            cors_origins=["https://example.com"],
        )


def test_production_accepts_long_admin_api_key():
    """A 32-char admin_api_key is accepted in production."""
    settings = Settings(
        environment="production",
        admin_api_key="x" * 32,
        jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
        cors_origins=["https://example.com"],
    )
    assert settings.admin_api_key == "x" * 32


def test_development_allows_short_admin_api_key():
    """Length check is production-only — dev environments can use any key."""
    settings = Settings(environment="development", admin_api_key="short")
    assert settings.admin_api_key == "short"
