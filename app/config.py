"""Application configuration via environment variables."""

import os
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
    database_url: str = "postgresql://atelier:atelier@localhost:5432/atelier_marie"

    # Database concurrency (design Decision 14). The psycopg pool and the Starlette
    # threadpool are sized together: threadpool >= pool so a threadpooled DB handler
    # never waits on a missing worker thread, only on a busy connection. Bounded
    # above by Postgres max_connections (~100) on a single free-tier VPS, leaving
    # headroom for migrations/admin. Pool wait timeout makes bursts queue then fail
    # clean rather than hang. Validated (not trusted) by the stress test.
    db_pool_min_size: int = Field(default=2, ge=1, le=100)
    db_pool_max_size: int = Field(default=20, ge=1, le=100)
    db_pool_timeout_seconds: float = Field(default=8.0, gt=0, le=60)
    server_threadpool_size: int = Field(default=24, ge=1, le=200)

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

    # Object storage (Cloudflare R2, S3-compatible) for product media.
    # Empty defaults keep the app bootable without R2 configured; only media
    # write/delete paths fail (with a clear config error) when unset. The R2
    # client is constructed only in app/services/object_storage_service.py.
    r2_bucket: str = ""
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_public_base_url: str = ""

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
    stripe_publishable_key: str = ""
    stripe_success_url: str = ""
    stripe_cancel_url: str = ""
    abandoned_card_review_hours: int = Field(default=24, ge=1, le=168)

    # Bank transfer (payment-integration)
    bank_iban: str = ""
    bank_bic: str = ""
    bank_name: str = ""

    # First-party analytics (first-party-funnel-analytics)
    analytics_enabled: bool = False
    analytics_data_dir: str = "./analytics-data"
    analytics_events_jsonl_path: str = "./analytics-data/events.jsonl"
    analytics_duckdb_path: str = "./analytics-data/analytics.duckdb"
    analytics_consent_version: str = "2026-07-31"
    analytics_batch_size: int = Field(default=25, ge=1, le=100)
    analytics_retention_days: int = Field(default=395, ge=1)
    analytics_delivery_tolerance: int = Field(default=0, ge=0)
    analytics_legal_approved: bool = False

    # Courier pricing APIs (shipping-pricing). Credentials are validated lazily
    # per-request - a misconfigured account produces fallback quotes with a
    # logged warning, never a startup failure (design Risks table).
    speedy_api_username: str = ""
    speedy_api_password: SecretStr = SecretStr("")
    # Speedy REST base URL - endpoints (/calculate, /shipment, /track, /print)
    # derive from it, so demo/prod is an env change (design Decision 1).
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
    econt_calculate_url: str = (
        "https://ee.econt.com/services/Shipments/LabelService.createLabel.json"
    )

    # Econt sender identity — the shop's fixed origin, sent in every Econt
    # calculate payload (name + phone + address). Not credentials: these are
    # the public "from" details of the shipment, so plain str with real
    # defaults (works in dev without a .env; still env-overridable).
    econt_sender_name: str = "Atelier Marie"
    econt_sender_phone: str = "0899869055"
    econt_sender_address: str = "жк Красно село ул. Царица Елеонора №12"
    econt_sender_city: str = "София"

    # Econt Delivery fulfillment API. These are separate from the pricing
    # credentials above: fulfillment uses Econt Delivery shop id + private code.
    econt_delivery_base_url: str = ""
    econt_delivery_private_key: SecretStr = SecretStr("")
    econt_delivery_shop_id: str = ""
    econt_office_locator_url: str = ""
    econt_office_locator_origins: list[str] = []
    econt_secret_encryption_key: SecretStr = SecretStr("")

    # Courier status polling. The poller is async-only and uses provider clients
    # directly; no worker-thread offload is used for courier HTTP calls.
    courier_polling_enabled: bool = True
    courier_polling_speedy_enabled: bool = True
    courier_polling_econt_enabled: bool = True
    courier_polling_interval_seconds: int = Field(default=300, ge=30, le=86_400)
    courier_polling_batch_size: int = Field(default=25, ge=1, le=100)
    courier_polling_lease_seconds: int = Field(default=120, ge=10, le=3_600)
    courier_polling_max_backoff_seconds: int = Field(default=3_600, ge=60, le=86_400)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        """Refuse to start in production with insecure defaults."""
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            msg = "DATABASE_URL must be a Postgres connection URL. SQLite is no longer supported."
            raise ValueError(msg)
        if self.db_pool_max_size < self.db_pool_min_size:
            msg = "DB_POOL_MAX_SIZE must be >= DB_POOL_MIN_SIZE."
            raise ValueError(msg)
        if self.server_threadpool_size < self.db_pool_max_size:
            msg = (
                "SERVER_THREADPOOL_SIZE must be >= DB_POOL_MAX_SIZE so a threadpooled "
                "handler never waits on a missing worker thread, only on a busy connection."
            )
            raise ValueError(msg)
        if self.environment == "production" and not os.getenv("DATABASE_URL"):
            msg = "DATABASE_URL must be set in production."
            raise ValueError(msg)
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
        if (
            self.environment == "production"
            and self.analytics_enabled
            and not self.analytics_legal_approved
        ):
            msg = "ANALYTICS_LEGAL_APPROVED must be true before enabling analytics in production."
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
