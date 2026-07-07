"""Shared test fixtures for Atelier Marie."""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import init_db


@pytest.fixture()
def db_path(tmp_path) -> str:
    """Return the path to the isolated test database."""
    return str(tmp_path / "test.db")


@pytest.fixture()
def app(db_path):
    """Create a FastAPI app configured for testing with an isolated database.

    Initializes the DB here because ASGITransport does not trigger ASGI
    lifespan events — the lifespan's init_db() only runs in production.
    """
    os.environ["DATABASE_PATH"] = db_path

    # Clear the cached settings so it rebuilds from the new env var
    get_settings.cache_clear()

    # Initialize DB (schema + module-level _db_path)
    init_db(db_path)

    from app.main import create_app

    test_app = create_app()

    yield test_app

    # Restore cache for next test
    get_settings.cache_clear()


@pytest.fixture()
def db(db_path):
    """Yield a raw sqlite3 connection to the test DB for state assertions."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Yield an async HTTP test client backed by the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
def session_id(app, db_path) -> str:
    """Insert a valid session row and return its ID for use in authenticated requests."""
    import sqlite3

    sid = "test-session-id"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, expires_at) VALUES (?, datetime('now', '+30 days'))",
        (sid,),
    )
    conn.commit()
    conn.close()
    return sid


@pytest.fixture()
async def auth_client(app, session_id) -> AsyncGenerator[AsyncClient, None]:
    """Yield a test client with a pre-existing session cookie set."""
    from app.config import get_settings

    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(settings.session_cookie_name, session_id)
        yield c
