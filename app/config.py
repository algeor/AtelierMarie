"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse

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
_LOCAL_DB_HOSTS = {"postgres", "localhost", "127.0.0.1", "::1"}
_INSECURE_DB_PASSWORDS = {"", "atelier", "postgres", "password", "changeme", "change-me"}
_INSECURE_SECRET_VALUES = {
    "",
    "change-me",
    "changeme",
    "change-me-in-production",
    "replace-me",
    "replace-with-a-long-random-secret",
    "replace-with-at-least-32-characters",
}
_SECRET_FILE_FIELDS = (
    ("database_url", "database_url_file"),
    ("migration_database_url", "migration_database_url_file"),
    ("jwt_secret", "jwt_secret_file"),
    ("google_client_secret", "google_client_secret_file"),
    ("admin_api_key", "admin_api_key_file"),
    ("email_api_key", "email_api_key_file"),
    ("zeptomail_webhook_auth_key", "zeptomail_webhook_auth_key_file"),
    ("stripe_secret_key", "stripe_secret_key_file"),
    ("stripe_webhook_secret", "stripe_webhook_secret_file"),
    ("speedy_api_password", "speedy_api_password_file"),
    ("econt_api_password", "econt_api_password_file"),
    ("econt_delivery_private_key", "econt_delivery_private_key_file"),
    ("econt_secret_encryption_key", "econt_secret_encryption_key_file"),
)


def _read_secret_file(path: str) -> str:
    """Read a single-value secret file, trimming only surrounding whitespace."""
    return Path(path).read_text(encoding="utf-8").strip()


def _database_host(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or ""


def _database_password(url: str) -> str:
    return urlparse(url).password or ""


def _database_sslmode(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return (query.get("sslmode") or [""])[0]


def _is_external_database(url: str) -> bool:
    host = _database_host(url)
    return bool(host and host not in _LOCAL_DB_HOSTS)


class Settings(BaseSettings):
    """All application settings. Loaded from env vars (or .env file)."""

    # Core
    environment: str = "development"
    database_url: str = "postgresql://atelier:atelier@localhost:5432/atelier_marie"
    database_url_file: str = ""
    migration_database_url: str = ""
    migration_database_url_file: str = ""

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
    jwt_secret_file: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 168  # 7 days
    jwt_cookie_name: str = "atelier_auth"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_client_secret_file: str = ""
    google_redirect_uri: str = ""
    frontend_url: str = "http://localhost:3000"

    # Admin
    admin_api_key: str = ""
    admin_api_key_file: str = ""

    # Email notifications
    email_provider: Literal["console", "zeptomail"] = "console"
    email_api_key: SecretStr = SecretStr("")  # ZeptoMail Send Mail token
    email_api_key_file: str = ""
    email_from_address: EmailStr = "orders@theateliermarie.com"  # root-domain alias
    email_from_name: str = "Atelier Marie"
    email_reply_to: EmailStr = "contacts@theateliermarie.com"  # Zoho human mailbox
    admin_notification_email: EmailStr | Literal[""] = ""  # empty = admin notifications disabled
    contact_message_retention_days: int = Field(default=365, ge=1)
    # ZeptoMail webhook signing key (bounce/complaint endpoint — follow-up)
    zeptomail_webhook_auth_key: SecretStr = SecretStr("")
    zeptomail_webhook_auth_key_file: str = ""

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
    stripe_secret_key_file: str = ""
    stripe_webhook_secret: str = ""
    stripe_webhook_secret_file: str = ""
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
    speedy_api_password_file: str = ""
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
    econt_api_password_file: str = ""
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
    econt_delivery_private_key_file: str = ""
    econt_delivery_shop_id: str = ""
    econt_office_locator_url: str = ""
    econt_office_locator_origins: list[str] = []
    econt_secret_encryption_key: SecretStr = SecretStr("")
    econt_secret_encryption_key_file: str = ""

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

    @model_validator(mode="before")
    @classmethod
    def load_secret_files(cls, values: object) -> object:
        """Allow production secrets to be supplied as mounted files."""
        if not isinstance(values, dict):
            return values
        data = dict(values)
        for target, file_key in _SECRET_FILE_FIELDS:
            file_path = data.get(file_key)
            if file_path:
                data[target] = _read_secret_file(str(file_path))
        return data

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
        if self.environment == "production" and not (self.database_url or self.database_url_file):
            msg = "DATABASE_URL must be set in production."
            raise ValueError(msg)
        if self.migration_database_url and not self.migration_database_url.startswith(
            ("postgresql://", "postgres://")
        ):
            msg = "MIGRATION_DATABASE_URL must be a Postgres connection URL."
            raise ValueError(msg)
        if self.environment == "production":
            password = _database_password(self.database_url)
            if password.lower() in _INSECURE_DB_PASSWORDS:
                msg = "DATABASE_URL must not use a default or weak database password in production."
                raise ValueError(msg)
            if _is_external_database(self.database_url) and not _database_sslmode(
                self.database_url
            ):
                msg = "External production DATABASE_URL must include sslmode=require or stronger."
                raise ValueError(msg)
            if self.migration_database_url:
                migration_password = _database_password(self.migration_database_url)
                if migration_password.lower() in _INSECURE_DB_PASSWORDS:
                    msg = (
                        "MIGRATION_DATABASE_URL must not use a default or weak database password "
                        "in production."
                    )
                    raise ValueError(msg)
                if _is_external_database(self.migration_database_url) and not _database_sslmode(
                    self.migration_database_url
                ):
                    msg = (
                        "External production MIGRATION_DATABASE_URL must include "
                        "sslmode=require or stronger."
                    )
                    raise ValueError(msg)
        if self.environment not in ("development", "test") and (
            self.jwt_secret == _DEV_JWT_SECRET
            or self.jwt_secret.lower() in _INSECURE_SECRET_VALUES
            or self.jwt_secret.lower().startswith("replace-with")
            or len(self.jwt_secret) < 32
        ):
            msg = (
                "JWT_SECRET must be set to a secure value of at least 32 characters "
                "outside development/test. Do not use the development default."
            )
            raise ValueError(msg)
        if self.environment == "production" and not self.admin_api_key:
            msg = "ADMIN_API_KEY must be set in production."
            raise ValueError(msg)
        if self.environment == "production" and (
            len(self.admin_api_key) < 32
            or self.admin_api_key.lower() in _INSECURE_SECRET_VALUES
            or self.admin_api_key.lower().startswith("replace-with")
        ):
            msg = (
                "ADMIN_API_KEY must be a real secure value of at least 32 characters "
                "in production."
            )
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
