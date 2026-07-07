"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

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

    # Session
    session_cookie_name: str = "session_id"
    session_max_age: int = 30 * 24 * 60 * 60  # 30 days in seconds

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        """Refuse to start in production with the dev JWT secret."""
        if self.environment == "production" and self.jwt_secret == _DEV_JWT_SECRET:
            msg = (
                "JWT_SECRET must be set to a secure value in production. "
                "Do not use the development default."
            )
            raise ValueError(msg)
        return self

@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Call get_settings.cache_clear() in tests."""
    return Settings()

