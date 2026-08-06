"""Fixtures for tests requiring the REAL session middleware.

Ported to the Postgres template-clone model (design Decision 15). These tests
run against the same per-worker Postgres database provisioned by the root
``tests/conftest.py`` (session-scoped ``worker_database_url``), but build the app
with the REAL session middleware rather than any fake/test session shim.

Current shape:

- ``db_path`` is the worker ``DATABASE_URL`` from the root conftest, and the app
  opens the psycopg pool via ``init_db(url)`` (the single chokepoint).
- ``_clean_tables`` is no longer a no-op — the root conftest's autouse truncation
  handles per-test isolation, so the local no-op override is removed.
- Realapp tests exercise the real ``SessionMiddleware``, so they do NOT rely on
  the fake-session row; each test drives session creation through the middleware.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

_REALAPP_DIR = str(Path(__file__).parent)

# Reuse the root harness's admin key so admin_client auth lines up.
ADMIN_API_KEY = "test-admin-key"  # pragma: allowlist secret


def pytest_collection_modifyitems(items):
    """Apply the integration marker to all tests in this directory."""
    for item in items:
        if str(item.fspath).startswith(_REALAPP_DIR):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def app(worker_database_url: str):
    """Session-scoped app with the REAL ``SessionMiddleware`` (no fake swap).

    Overrides the root ``app`` fixture (which installs ``FakeSessionMiddleware``)
    so realapp tests exercise real session creation through the middleware. Binds
    ``DATABASE_URL`` to this worker's Postgres DB and opens the pool via
    ``init_db`` — the single chokepoint — exactly like the root fixture, but skips
    the ASGI middleware swap.
    """
    import os

    from app.config import get_settings
    from app.database import close_db, init_db

    os.environ["DATABASE_URL"] = worker_database_url
    os.environ["ADMIN_API_KEY"] = ADMIN_API_KEY
    get_settings.cache_clear()
    init_db(worker_database_url)

    from app.main import create_app

    test_app = create_app()
    yield test_app

    close_db()
    get_settings.cache_clear()


@pytest.fixture()
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with admin Bearer auth (realapp/real middleware)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"
        yield c
