"""Alembic migration-state verification helpers."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.config import get_settings


class MigrationStateError(RuntimeError):
    """Raised when the connected database is not at the expected Alembic head."""


def sqlalchemy_url(database_url: str) -> str:
    """Return a SQLAlchemy URL that uses psycopg v3 for Postgres connections.

    The password is preserved: this value is passed to create_engine() to open a
    real connection. Use masked_sqlalchemy_url() for anything that gets logged.
    """
    url = make_url(database_url)
    if url.drivername in {"postgresql", "postgres"}:
        url = url.set(drivername="postgresql+psycopg")
    if not url.drivername.startswith("postgresql"):
        msg = "DATABASE_URL must be a Postgres URL. SQLite is no longer supported."
        raise MigrationStateError(msg)
    return url.render_as_string(hide_password=False)


def masked_sqlalchemy_url(database_url: str) -> str:
    """Return the SQLAlchemy URL with the password masked, for logging only."""
    return make_url(sqlalchemy_url(database_url)).render_as_string(hide_password=True)


def alembic_config() -> Config:
    """Build an Alembic Config rooted at the repository migration files."""
    root = Path(__file__).resolve().parents[1]
    return Config(str(root / "alembic.ini"))


def script_heads() -> set[str]:
    """Return Alembic head revisions declared by the migration script directory."""
    script = ScriptDirectory.from_config(alembic_config())
    return set(script.get_heads())


def current_database_heads(database_url: str | None = None) -> set[str]:
    """Return current Alembic revisions recorded in the connected database."""
    database_url = database_url or get_settings().database_url
    engine = create_engine(sqlalchemy_url(database_url), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return set(context.get_current_heads())
    finally:
        engine.dispose()


def verify_database_at_head(database_url: str | None = None) -> None:
    """Fail clearly unless the connected database exactly matches Alembic head."""
    expected = script_heads()
    current = current_database_heads(database_url)
    if current == expected:
        return
    if not current:
        msg = (
            "Database has no Alembic revision. Run `alembic upgrade head` "
            "before starting the backend."
        )
    else:
        msg = (
            "Database Alembic revision mismatch. "
            f"current={sorted(current)} expected={sorted(expected)}. "
            "Run `alembic upgrade head` and verify there is no divergent migration branch."
        )
    raise MigrationStateError(msg)
