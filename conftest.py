"""Shared test fixtures for Atelier Marie.

Fixture scoping strategy:
- Module-scoped: app, client, db, admin_client, service_db (one init_db per file)
- Function-scoped (autouse): _clean_tables (DELETE between tests for isolation)
- Function-scoped: session tests only (test_session.py, test_session_hardened.py)

FakeSessionMiddleware replaces real session middleware in route tests to avoid
per-request DB round-trips. Real middleware is tested in its own test files.
"""

import sqlite3
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import init_db

# ===========================================================================
# Constants
# ===========================================================================

_DT_FMT = "%Y-%m-%d %H:%M:%S"

ADMIN_API_KEY = "test-admin-key-fixture"

DEFAULT_PRODUCTS = [
    {
        "id": "lavender-dream-300ml",
        "name": "Lavender Dream",
        "description": "A calming lavender candle",
        "price_cents": 3200,
        "category": "luxury-jar",
        "stock": 24,
    },
    {
        "id": "midnight-amber-300ml",
        "name": "Midnight Amber",
        "description": "Warm amber and sandalwood",
        "price_cents": 4500,
        "category": "luxury-jar",
        "stock": 12,
    },
    {
        "id": "vanilla-brulee-200ml",
        "name": "Vanilla Crème Brûlée",
        "description": "Rich vanilla custard dessert candle",
        "price_cents": 2800,
        "category": "dessert",
        "stock": 0,
    },
]


# ===========================================================================
# FakeSessionMiddleware
# ===========================================================================


class FakeSessionMiddleware(BaseHTTPMiddleware):
    """Stamps a fixed session_id without DB or cookie logic.

    Used in route tests to eliminate per-request DB overhead from session
    management. The real middleware is tested separately in test_session*.py.
    """

    def __init__(self, app, session_id: str):
        super().__init__(app)
        self._session_id = session_id

    async def dispatch(self, request, call_next):
        request.state.session_id = self._session_id
        request.state.session_is_new = False
        return await call_next(request)


# ===========================================================================
# Helper functions (not fixtures — called explicitly by tests)
# ===========================================================================


def make_session(conn: sqlite3.Connection, session_id: str | None = None) -> str:
    """Insert a session row and return its ID.

    If no session_id is provided, generates a UUID4.
    """
    sid = session_id or str(uuid.uuid4())
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=30)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (sid, now.strftime(_DT_FMT), expires_at.strftime(_DT_FMT)),
    )
    conn.commit()
    return sid


def seed_products(conn: sqlite3.Connection, products: list[dict] | None = None) -> None:
    """Insert product rows from a list of dicts.

    If no products list is provided, inserts DEFAULT_PRODUCTS.
    """
    items = products if products is not None else DEFAULT_PRODUCTS
    for p in items:
        conn.execute(
            "INSERT INTO products (id, name_en, description_en, price_cents, "
            "category, stock, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (
                p["id"],
                p["name"],
                p.get("description", ""),
                p["price_cents"],
                p.get("category", ""),
                p.get("stock", 0),
                1 if p.get("is_active", True) else 0,
            ),
        )
    conn.commit()


# ===========================================================================
# Module-scoped core fixtures
# ===========================================================================


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (built-in is function-scoped only)."""
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> str:
    """Return the path to the isolated test database (one per module)."""
    tmp = tmp_path_factory.mktemp("db")
    return str(tmp / "test.db")


@pytest.fixture(scope="module")
def app(db_path, monkeypatch_module):
    """Create a FastAPI app configured for testing with an isolated database.

    Module-scoped: init_db + create_app runs once per test file.
    Uses FakeSessionMiddleware to avoid per-request DB session overhead.
    """
    monkeypatch_module.setenv("DATABASE_PATH", db_path)
    monkeypatch_module.setenv("ADMIN_API_KEY", ADMIN_API_KEY)

    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app

    test_app = create_app()

    # Replace real session middleware with fake one.
    # FastAPI stores middleware as app.user_middleware list, but for an already-built
    # app we need to replace at the ASGI stack level. The simplest approach: create
    # a session in the DB and use FakeSessionMiddleware that stamps that ID.
    fake_session_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (fake_session_id, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.commit()
    conn.close()

    # Rebuild app middleware stack with fake session middleware
    from starlette.middleware import Middleware

    # Remove the real SessionMiddleware and add fake one
    test_app.user_middleware = [
        m for m in test_app.user_middleware if "SessionMiddleware" not in str(m.cls.__name__)
    ]
    test_app.user_middleware.append(Middleware(FakeSessionMiddleware, session_id=fake_session_id))
    # Force middleware stack rebuild
    test_app.middleware_stack = None
    test_app.middleware_stack = test_app.build_middleware_stack()

    # Stash session_id on the app for tests that need it
    test_app._test_session_id = fake_session_id

    yield test_app

    get_settings.cache_clear()


@pytest.fixture(scope="module")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Module-scoped async HTTP test client backed by the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(scope="module")
def db(db_path) -> sqlite3.Connection:
    """Module-scoped raw sqlite3 connection to the test DB."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def service_db(tmp_path_factory) -> sqlite3.Connection:
    """Module-scoped raw connection for service-layer tests (no app, no middleware).

    Creates its own DB file and initializes schema. Tests use helper functions
    to seed data as needed.
    """
    tmp = tmp_path_factory.mktemp("service_db")
    path = str(tmp / "service.db")
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


@pytest.fixture(scope="module")
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Module-scoped async HTTP client with admin Bearer auth header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"
        yield c


# ===========================================================================
# Per-test cleanup (autouse)
# ===========================================================================


@pytest.fixture(autouse=True)
def _clean_tables(db_path, app):
    """Delete all data between tests (module-scoped DB persists).

    Runs after each test. Tables deleted in FK-safe order (children first).
    FTS5 stays in sync via existing DELETE triggers.
    Preserves the fake session row used by FakeSessionMiddleware.
    """
    yield
    fake_session_id = getattr(app, "_test_session_id", None)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    for table in ("order_items", "orders", "cart_items"):
        conn.execute(f"DELETE FROM {table}")  # noqa: S608
    # Delete sessions except the fake middleware session
    if fake_session_id:
        conn.execute("DELETE FROM sessions WHERE id != ?", (fake_session_id,))
        # Unlink fake session from user before deleting users
        conn.execute("UPDATE sessions SET user_id = NULL WHERE id = ?", (fake_session_id,))
    else:
        conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM products")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


# ===========================================================================
# Legacy function-scoped fixtures (for session tests + backward compat)
# ===========================================================================


@pytest.fixture()
def session_id(app) -> str:
    """Return the fake session ID used by FakeSessionMiddleware.

    This session already exists in the DB (created by the app fixture).
    Tests that need a session_id for OAuth state, DB lookups, etc. get the
    same ID that the middleware stamps on every request.
    """
    return app._test_session_id


@pytest.fixture()
async def auth_client(app, session_id) -> AsyncGenerator[AsyncClient, None]:
    """Yield a test client with a pre-existing session cookie set."""
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(settings.session_cookie_name, session_id)
        yield c
