"""Application configuration via environment variables."""

import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

_logger = logging.getLogger(__name__)

_DEV_JWT_SECRET = "dev-secret-do-not-use-in-production"  # noqa: S105


class Settings(BaseSettings):
    """All application settings. Loaded from env vars (or .env file)."""

    # Core
    environment: str = "development"
    database_path: str = "./atelier_marie.db"

    # Auth
    jwt_secret: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    google_client_id: str = ""
    google_client_secret: str = ""

    # Admin
    admin_api_key: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Static files
    static_file_path: str = "./static"

    # Session
    session_cookie_name: str = "session_id"
    session_max_age: int = 30 * 24 * 60 * 60  # 30 days in seconds
    session_absolute_lifetime: int = 180 * 24 * 60 * 60  # 180 days in seconds
    session_sliding_threshold: int = 7 * 24 * 60 * 60  # 7 days in seconds

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
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Call get_settings.cache_clear() in tests."""
    return Settings()
