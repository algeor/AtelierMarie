"""Fixtures for tests requiring the REAL session middleware.

Function-scoped: each test gets its own database, app, and client.
This subdirectory isolates the cost of per-test init_db + full middleware.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import init_db

_REALAPP_DIR = str(Path(__file__).parent)


def pytest_collection_modifyitems(items):
    """Apply the integration marker to all tests in this directory."""
    for item in items:
        if str(item.fspath).startswith(_REALAPP_DIR):
            item.add_marker(pytest.mark.integration)


_DT_FMT = "%Y-%m-%d %H:%M:%S"

ADMIN_API_KEY = "test-admin-key-realapp"


@pytest.fixture()
def db_path(tmp_path) -> str:
    """Function-scoped DB path (fresh DB per test)."""
    return str(tmp_path / "test.db")


@pytest.fixture()
def app(db_path, monkeypatch):
    """Function-scoped app with REAL session middleware."""
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_API_KEY)
    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app

    test_app = create_app()
    yield test_app
    get_settings.cache_clear()


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Function-scoped async HTTP client with real middleware."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Function-scoped async HTTP client with admin Bearer auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"
        yield c


@pytest.fixture(autouse=True)
def _clean_tables():
    """No-op: function-scoped DB means each test starts fresh — no cleanup needed."""
    yield
