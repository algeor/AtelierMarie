"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

import structlog
from pydantic import EmailStr, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings

from app.constants import (
    SESSION_ABSOLUTE_LIFETIME_DAYS,
    SESSION_MAX_AGE_DAYS,
    SESSION_SLIDING_THRESHOLD_DAYS,
)

_logger = structlog.get_logger(__name__)

_DEV_JWT_SECRET = "dev-secret-do-not-use-in-production"  # noqa: S105


class Settings(BaseSettings):
    """All application settings. Loaded from env vars (or .env file)."""

    # Core
    environment: str = "development"
    database_path: str = "./atelier_marie.db"

    # Auth
    jwt_secret: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 168  # 7 days
    jwt_cookie_name: str = "atelier_auth"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    frontend_url: str = "http://localhost:3000"

    # Admin
    admin_api_key: str = ""

    # Email notifications
    email_provider: Literal["console", "zeptomail"] = "console"
    email_api_key: SecretStr = SecretStr("")  # ZeptoMail Send Mail token
    email_from_address: EmailStr = "orders@theateliermarie.com"  # root-domain alias
    email_from_name: str = "Atelier Marie"
    email_reply_to: EmailStr = "contacts@theateliermarie.com"  # Zoho human mailbox
    admin_notification_email: EmailStr | Literal[""] = ""  # empty = admin notifications disabled
    contact_message_retention_days: int = Field(default=365, ge=1)
    # ZeptoMail webhook signing key (bounce/complaint endpoint — follow-up)
    zeptomail_webhook_auth_key: SecretStr = SecretStr("")

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Static files
    static_file_path: str = "./static"

    # Product video processing
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    video_upload_temp_path: str = "./video-temp"
    max_video_upload_bytes: int = Field(default=200 * 1024 * 1024, gt=0)
    max_video_duration_seconds: int = Field(default=30, gt=0)

    # Session
    session_cookie_name: str = "session_id"
    session_max_age: int = SESSION_MAX_AGE_DAYS * 24 * 60 * 60
    session_absolute_lifetime: int = SESSION_ABSOLUTE_LIFETIME_DAYS * 24 * 60 * 60
    session_sliding_threshold: int = SESSION_SLIDING_THRESHOLD_DAYS * 24 * 60 * 60
    session_cookie_secure: bool = True
    session_skip_paths: list[str] = [
        "/health",
        "/v1/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/v1/docs",
        "/v1/redoc",
        "/v1/openapi.json",
        "/v1/webhooks/zeptomail",
        "/v1/webhooks/stripe",
    ]

    # Cart limits
    cart_max_quantity_per_item: int = 10
    cart_max_distinct_items: int = 20

    # Stripe (payment-integration)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = ""
    stripe_cancel_url: str = ""

    # Bank transfer (payment-integration)
    bank_iban: str = ""
    bank_bic: str = ""
    bank_name: str = ""

    # Courier pricing APIs (shipping-pricing). Credentials are validated lazily
    # per-request — a misconfigured account produces fallback quotes with a
    # logged warning, never a startup failure (design Risks table).
    speedy_api_username: str = ""
    speedy_api_password: SecretStr = SecretStr("")
    # Speedy REST base URL — endpoints (/calculate, /shipment, /track, /print)
    # derive from it, so demo↔prod is an env change (design Decision 1).
    speedy_base_url: str = "https://api.speedy.bg/v1"
    # Speedy's numeric registered-client/contract identifier, sent as
    # `sender.clientId` on every calculate/shipment request. Distinct from the
    # API login (`speedy_api_username`): renamed from the former
    # `speedy_sender_office_id`, which was named/populated as an office slug and
    # let an empty non-numeric value reach Speedy on every call (design Decision 1).
    speedy_client_id: str = ""
    econt_api_username: str = ""
    econt_api_password: SecretStr = SecretStr("")
    econt_sender_office_id: str = ""

    # Econt sender identity — the shop's fixed origin, sent in every Econt
    # calculate payload (name + phone + address). Not credentials: these are
    # the public "from" details of the shipment, so plain str with real
    # defaults (works in dev without a .env; still env-overridable).
    econt_sender_name: str = "Atelier Marie"
    econt_sender_phone: str = "0899869055"
    econt_sender_address: str = "жк Красно село ул. Царица Елеонора №12"
    econt_sender_city: str = "София"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        """Refuse to start in production with insecure defaults."""
        if self.jwt_secret == _DEV_JWT_SECRET and self.environment not in (
            "development",
            "test",
        ):
            msg = (
                "JWT_SECRET must be set to a secure value in production. "
                "Do not use the development default."
            )
            raise ValueError(msg)
        if self.environment == "production" and not self.admin_api_key:
            msg = "ADMIN_API_KEY must be set in production."
            raise ValueError(msg)
        if self.environment == "production" and len(self.admin_api_key) < 32:
            msg = "ADMIN_API_KEY must be at least 32 characters in production."
            raise ValueError(msg)
        if self.environment == "production" and "*" in self.cors_origins:
            msg = "CORS wildcard '*' is not allowed in production."
            raise ValueError(msg)
        if self.environment == "production" and not (
            self.google_client_id and self.google_client_secret
        ):
            _logger.warning(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not set in production. "
                "Google OAuth will be unavailable."
            )
        if self.email_provider == "zeptomail" and not self.email_api_key.get_secret_value():
            _logger.warning(
                "EMAIL_PROVIDER is set to zeptomail but EMAIL_API_KEY is empty. "
                "Email sending will be unavailable."
            )
        if self.environment == "production" and not (
            self.speedy_api_username
            and self.speedy_api_password.get_secret_value()
            and self.speedy_client_id.isdigit()
        ):
            _logger.warning(
                "SPEEDY_API_USERNAME / SPEEDY_API_PASSWORD / SPEEDY_CLIENT_ID (numeric) "
                "not fully set in production. Speedy live pricing and shipment "
                "creation will be unavailable (quotes degrade to the flat fallback)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Call get_settings.cache_clear() in tests."""
    return Settings()
