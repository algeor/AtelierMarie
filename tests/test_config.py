"""Tests for Settings validators in app/config.py."""

import pytest

from app.config import Settings
from app.migration_state import masked_sqlalchemy_url, sqlalchemy_url

SECURE_LOCAL_DATABASE_URL = "postgresql://atelier:strong-db-password@localhost:5432/atelier_marie"


def test_production_rejects_short_admin_api_key():
    """In production, ADMIN_API_KEY must be at least 32 characters."""
    with pytest.raises(ValueError, match="32 characters"):
        Settings(
            environment="production",
            database_url=SECURE_LOCAL_DATABASE_URL,
            admin_api_key="short",
            jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
            cors_origins=["https://example.com"],
        )


def test_production_accepts_long_admin_api_key():
    """A 32-char admin_api_key is accepted in production."""
    settings = Settings(
        environment="production",
        database_url=SECURE_LOCAL_DATABASE_URL,
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
            database_url=SECURE_LOCAL_DATABASE_URL,
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
        database_url=SECURE_LOCAL_DATABASE_URL,
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


def test_database_url_file_populates_database_url(tmp_path):
    secret_file = tmp_path / "database_url"
    secret_file.write_text(
        "postgresql://atelier:file-secret@localhost:5432/atelier_marie\n",
        encoding="utf-8",
    )

    settings = Settings(database_url_file=str(secret_file))

    assert settings.database_url == "postgresql://atelier:file-secret@localhost:5432/atelier_marie"


def test_migration_database_url_file_populates_migration_database_url(tmp_path):
    secret_file = tmp_path / "migration_database_url"
    secret_file.write_text(
        "postgresql://atelier_migrator:file-secret@localhost:5432/atelier_marie\n",
        encoding="utf-8",
    )

    settings = Settings(migration_database_url_file=str(secret_file))

    assert (
        settings.migration_database_url
        == "postgresql://atelier_migrator:file-secret@localhost:5432/atelier_marie"
    )


def test_plain_secret_files_populate_string_settings(tmp_path):
    jwt_file = tmp_path / "jwt_secret"
    admin_file = tmp_path / "admin_api_key"
    google_file = tmp_path / "google_client_secret"
    jwt_file.write_text("jwt-secret-from-file-32-characters-minimum", encoding="utf-8")
    admin_file.write_text("admin-api-key-from-file-32-characters-minimum", encoding="utf-8")
    google_file.write_text("google-client-secret-from-file", encoding="utf-8")

    settings = Settings(
        jwt_secret_file=str(jwt_file),
        admin_api_key_file=str(admin_file),
        google_client_secret_file=str(google_file),
    )

    assert settings.jwt_secret == "jwt-secret-from-file-32-characters-minimum"
    assert settings.admin_api_key == "admin-api-key-from-file-32-characters-minimum"
    assert settings.google_client_secret == "google-client-secret-from-file"


def test_secretstr_secret_files_populate_secret_settings(tmp_path):
    email_file = tmp_path / "email_api_key"
    speedy_file = tmp_path / "speedy_api_password"
    econt_file = tmp_path / "econt_delivery_private_key"
    email_file.write_text("email-secret-from-file", encoding="utf-8")
    speedy_file.write_text("speedy-password-from-file", encoding="utf-8")
    econt_file.write_text("econt-private-key-from-file", encoding="utf-8")

    settings = Settings(
        email_api_key_file=str(email_file),
        speedy_api_password_file=str(speedy_file),
        econt_delivery_private_key_file=str(econt_file),
    )

    assert settings.email_api_key.get_secret_value() == "email-secret-from-file"
    assert settings.speedy_api_password.get_secret_value() == "speedy-password-from-file"
    assert settings.econt_delivery_private_key.get_secret_value() == "econt-private-key-from-file"


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(
            environment="production",
            database_url=SECURE_LOCAL_DATABASE_URL,
            admin_api_key="x" * 32,
            jwt_secret="too-short",
            cors_origins=["https://example.com"],
        )


def test_production_rejects_placeholder_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(
            environment="production",
            database_url=SECURE_LOCAL_DATABASE_URL,
            admin_api_key="x" * 32,
            jwt_secret="replace-with-a-long-random-secret",
            cors_origins=["https://example.com"],
        )


def test_production_rejects_placeholder_admin_api_key():
    with pytest.raises(ValueError, match="ADMIN_API_KEY"):
        Settings(
            environment="production",
            database_url=SECURE_LOCAL_DATABASE_URL,
            admin_api_key="replace-with-at-least-32-characters",
            jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
            cors_origins=["https://example.com"],
        )


def test_production_rejects_default_database_password():
    with pytest.raises(ValueError, match="default or weak database password"):
        Settings(
            environment="production",
            database_url="postgresql://atelier:atelier@postgres:5432/atelier_marie",
            admin_api_key="x" * 32,
            jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
            cors_origins=["https://example.com"],
        )


def test_production_rejects_external_database_without_sslmode():
    with pytest.raises(ValueError, match="External production DATABASE_URL"):
        Settings(
            environment="production",
            database_url="postgresql://atelier:strong-db-password@db.example.com:5432/atelier_marie",
            admin_api_key="x" * 32,
            jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
            cors_origins=["https://example.com"],
        )


def test_production_accepts_external_database_with_sslmode():
    settings = Settings(
        environment="production",
        database_url=(
            "postgresql://atelier:strong-db-password@db.example.com:5432/atelier_marie"
            "?sslmode=require"
        ),
        admin_api_key="x" * 32,
        jwt_secret="a-secure-jwt-secret-not-the-dev-default-!!",
        cors_origins=["https://example.com"],
    )

    assert settings.database_url.endswith("sslmode=require")


def test_sqlalchemy_url_preserves_password_for_connecting():
    """The connection URL must keep the real password (it is fed to create_engine)."""
    rendered = sqlalchemy_url("postgresql://atelier:super-secret@localhost:5432/atelier_marie")

    assert "super-secret" in rendered
    assert rendered.startswith("postgresql+psycopg://")


def test_masked_sqlalchemy_url_hides_database_password():
    rendered = masked_sqlalchemy_url(
        "postgresql://atelier:super-secret@localhost:5432/atelier_marie"
    )

    assert "super-secret" not in rendered
    assert "***" in rendered
