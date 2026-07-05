"""Shared test fixtures for Atelier Marie."""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import init_db


@pytest.fixture()
def db_path(tmp_path) -> str:
    """Create a fresh SQLite database in a temp directory with schema initialized."""
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture()
def app(db_path: str):
    """Create a FastAPI app configured for testing with an isolated database."""
    # Override settings before importing app
    os.environ["DATABASE_PATH"] = db_path

    # Re-import to pick up the overridden env var
    import app.config
    from app.config import Settings as _Settings

    app.config.settings = _Settings()

    # Patch the database module path
    import app.database

    app.database._db_path = db_path

    from app.main import create_app

    test_app = create_app()
    return test_app


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Yield an async HTTP test client backed by the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
