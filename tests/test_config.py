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


def test_production_rejects_analytics_without_legal_approval():
    """Production analytics must not start until legal approval is explicit."""
    with pytest.raises(ValueError, match="ANALYTICS_LEGAL_APPROVED"):
        Settings(
            environment="production",
            admin_api_key="x" * 32,
            jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
            cors_origins=["https://example.com"],
            analytics_enabled=True,
            analytics_legal_approved=False,
        )


def test_production_accepts_analytics_after_legal_approval():
    """Legal approval flag unlocks production analytics startup."""
    settings = Settings(
        environment="production",
        admin_api_key="x" * 32,
        jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
        cors_origins=["https://example.com"],
        analytics_enabled=True,
        analytics_legal_approved=True,
    )
    assert settings.analytics_enabled is True


def test_development_allows_short_admin_api_key():
    """Length check is production-only — dev environments can use any key."""
    settings = Settings(environment="development", admin_api_key="short")
    assert settings.admin_api_key == "short"


def test_admin_notification_email_must_be_empty_or_valid_email():
    Settings(admin_notification_email="")
    Settings(admin_notification_email="owner@example.com")

    with pytest.raises(ValueError):
        Settings(admin_notification_email="not-an-email")


def test_contact_message_retention_days_must_be_positive():
    with pytest.raises(ValueError):
        Settings(contact_message_retention_days=0)
