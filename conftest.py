"""Central Postgres test provisioning (design Decision 15).

This is the single shared test harness for the backend suite (the canonical
repo-root ``conftest.py``). It replaces the former SQLite fixtures (per-file
``init_db(db_path)`` against a ``:memory:`` or tmp-file database) with a
template-clone-per-worker model against a real, already-reachable Postgres.

Mechanics (Decision 15):

- **Migrated template, cloned per worker.** ``init_db(path)`` no longer builds a
  schema from a file path; schema comes only from ``alembic upgrade head``. A
  session-scoped setup migrates one *template database* once, then each
  pytest-xdist worker does ``CREATE DATABASE <worker_db> TEMPLATE <template>`` — a
  near-instant, Postgres-native file copy. The worker DB name derives from
  ``PYTEST_XDIST_WORKER`` (single-name fallback when xdist is off).
- **Session-scoped provisioning.** ``worker_database_url``, ``db_path`` (the
  worker ``DATABASE_URL``), and ``app`` are session-scoped (session = one worker
  process), so the worker database and psycopg pool are created once per worker.
  The database no longer resets at module boundaries — only ``_clean_tables``
  (autouse, per test) resets state. The raw-connection fixtures ``db`` /
  ``service_db`` stay function-scoped so a held transaction never blocks the next
  test's ``TRUNCATE``.
- **Truncate volatile tables only.** ``_clean_tables`` runs
  ``TRUNCATE <volatile tables> RESTART IDENTITY CASCADE``. The structural seed
  rows (taxonomy, FAQ, legal/cookies pages, site banner, delivery/Econt/inventory
  settings, about content) live inside the initial migration and are carried into
  every worker DB by the clone; those tables are deliberately excluded from the
  truncate set so their rows persist. There are no ``_seed_*`` re-seed calls.
- **Reachable Postgres required.** Postgres has no in-memory mode and the SQLite
  dialect is gone (Decision 1), so there is no zero-infra path: tests assume a
  Postgres is reachable via ``DATABASE_URL`` (locally ``docker compose up -d
  postgres``; CI provides a service container).

This is test-infra work only (Tasks 6.1-6.3); it is not part of the app
``?``->``%s`` sweep. ``get_db()`` remains the single connection chokepoint —
service signatures are untouched.

Consolidation note: this file previously lived in two places (a SQLite root
``conftest.py`` and a Postgres ``tests/conftest.py`` that silently shadowed it —
root wins when both load same-named fixtures, so the port had no effect). The
Postgres port now lives here alone; the duplicate ``tests/conftest.py`` was
deleted. ``from conftest import ADMIN_API_KEY`` (test_auth.py) resolves to this
file's constant.
"""

import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from psycopg.rows import dict_row
from starlette.middleware import Middleware

from app.config import get_settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
#
# ADMIN_API_KEY is imported directly by tests/test_auth.py via
# ``from conftest import ADMIN_API_KEY``; its value must stay stable. The app
# fixture exports it to the ``ADMIN_API_KEY`` env var so require_admin resolves
# the same string.
ADMIN_API_KEY = "test-admin-key-fixture"

# Fake-session row for FakeSessionMiddleware route tests. The ASGI-level
# middleware swap is DB-agnostic; the one row it needs is inserted via psycopg
# after clone (Decision 15).
FAKE_SESSION_ID = "test-session"


# ---------------------------------------------------------------------------
# Volatile-table allowlist (Decision 15)
# ---------------------------------------------------------------------------
#
# The truncate set is a curated allowlist of volatile/data tables, expressed as
# "every base table EXCEPT the migration-seed tables". The seed tables below hold
# structural default rows written by the initial migration (20260802_0001); the
# template clone carries them into each worker DB, so truncation must never touch
# them (otherwise the seeded rows vanish and there is nothing to re-seed).
#
# ``alembic_version`` is Alembic bookkeeping and is likewise never truncated.
#
# If a test mutates a seeded singleton (e.g. ``site_banners``,
# ``delivery_settings``), the fix is to move that one table into the volatile set
# AND give it an explicit per-table re-seed step — decided per table, not
# globally (Decision 15).
_SEED_TABLES: frozenset[str] = frozenset(
    {
        "product_types",
        "product_categories",
        "product_labels",
        "faq_sections",
        "faq_items",
        "terms_page",
        "terms_sections",
        "privacy_page",
        "privacy_sections",
        "cookies_page",
        "cookies_inventory",
        "cookies_sections",
        "site_banners",
        "delivery_settings",
        "econt_settings",
        "inventory_settings",
        "about_sections",
        "about_items",
    }
)

_NEVER_TRUNCATE: frozenset[str] = _SEED_TABLES | {"alembic_version"}


# ---------------------------------------------------------------------------
# FakeSessionMiddleware
# ---------------------------------------------------------------------------


class FakeSessionMiddleware:
    """Minimal ASGI middleware resolving every request to ``FAKE_SESSION_ID``.

    Route tests in ``tests/`` (as opposed to ``tests/realapp/``) are cookieless
    and must not pay a per-request DB round-trip to mint/read a session. The real
    ``SessionMiddleware`` would create a fresh UUID4 per request and orphan the
    seeded fake-session row. This middleware instead pins the request to the row
    inserted by ``_insert_fake_session`` after the template clone, setting the
    same ``request.state`` keys the real middleware sets (``session_id``,
    ``session_is_new``, ``preferred_locale``) so downstream code is unchanged.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            state = scope.setdefault("state", {})
            state["session_id"] = FAKE_SESSION_ID
            state["session_is_new"] = False
            state["preferred_locale"] = "en"
        await self.app(scope, receive, send)


def _install_fake_session_middleware(test_app) -> None:
    """Swap the real ``SessionMiddleware`` for ``FakeSessionMiddleware``.

    Edits ``app.user_middleware`` in place (replacing the ``SessionMiddleware``
    entry) and rebuilds the ASGI stack. Preserves middleware order — the real
    ``SessionMiddleware`` is added first so it runs closest to the routes, and the
    fake takes that same slot.
    """
    from app.middleware.session import SessionMiddleware

    replaced = False
    for index, middleware in enumerate(test_app.user_middleware):
        if middleware.cls is SessionMiddleware:
            test_app.user_middleware[index] = Middleware(FakeSessionMiddleware)
            replaced = True
            break
    if not replaced:  # pragma: no cover - guards against wiring drift
        raise RuntimeError(
            "SessionMiddleware not found in app.user_middleware; "
            "FakeSessionMiddleware swap failed (create_app wiring changed?)"
        )
    test_app.middleware_stack = test_app.build_middleware_stack()


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def _admin_url(database_url: str) -> str:
    """Return a connection URL pointing at the ``postgres`` maintenance DB.

    ``CREATE DATABASE`` cannot run inside the target database or a transaction,
    so template creation and per-worker cloning connect to the server's default
    maintenance database instead.
    """
    return _with_dbname(database_url, "postgres")


def _with_dbname(database_url: str, dbname: str) -> str:
    """Return ``database_url`` with its database name replaced by ``dbname``.

    Manipulates the URL in place (not via ``make_conninfo``) so the
    ``postgresql://`` scheme is preserved — ``app.config`` validates that the
    URL keeps that scheme.
    """
    parts = urlsplit(database_url)
    new_path = "/" + dbname
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))


def _base_dbname(database_url: str) -> str:
    """Return the database name component of ``database_url``."""
    return urlsplit(database_url).path.lstrip("/")


def _worker_id() -> str:
    """Return the pytest-xdist worker id, or ``master`` when xdist is off."""
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def _template_dbname(base: str) -> str:
    """Return the shared template database name for this test run."""
    return f"{base}_tmpl"


def _worker_dbname(base: str) -> str:
    """Return this worker's isolated database name."""
    return f"{base}_{_worker_id()}"


def _run_maintenance(admin_url: str, statement: sql.Composable) -> None:
    """Execute a single autocommit maintenance statement (CREATE/DROP DATABASE)."""
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(statement)


def _database_exists(admin_url: str, dbname: str) -> bool:
    with psycopg.connect(admin_url, autocommit=True) as conn:
        row = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Template migration (session-scoped, once per worker process)
# ---------------------------------------------------------------------------
#
# Under xdist each worker is a separate process, so this runs once per worker.
# The template only needs migrating once for the whole run, but concurrent
# workers must not race the CREATE. We serialize via an advisory lock on the
# maintenance connection and treat "already exists / already migrated" as success.


def _migrate_template(base_url: str) -> str:
    """Ensure a migrated template database exists; return its URL.

    Serialized across workers with a session advisory lock so exactly one worker
    creates and migrates the template; the rest observe it already present.
    """
    admin_url = _admin_url(base_url)
    base = _base_dbname(base_url)
    template = _template_dbname(base)
    template_url = _with_dbname(base_url, template)

    lock_key = 0x41_4D_54_50  # "AMTP" — AtelierMarie Template Provisioning
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
        try:
            if not _database_exists(admin_url, template):
                conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(template)))
                try:
                    _alembic_upgrade_head(template_url)
                except Exception:
                    # A half-created (empty/partial) template must not survive:
                    # a later run would see it "exists" and skip migration.
                    conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(template)))
                    raise
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
    return template_url


def _alembic_upgrade_head(database_url: str) -> None:
    """Run ``alembic upgrade head`` against ``database_url`` in-process."""
    from alembic.config import Config

    from alembic import command

    alembic_ini = Path(__file__).resolve().parent / "alembic.ini"
    config = Config(str(alembic_ini))
    # Alembic env.py reads the URL from settings/env; pin it explicitly so we
    # migrate the freshly created template rather than the default DATABASE_URL.
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["database_url"] = database_url
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    command.upgrade(config, "head")


def _clone_worker_db(base_url: str, template_url: str) -> str:
    """Create this worker's DB from the template and return its URL.

    ``CREATE DATABASE <worker> TEMPLATE <template>`` is a Postgres-native file
    copy — near-instant and independent of migration-chain length.
    """
    admin_url = _admin_url(base_url)
    base = _base_dbname(base_url)
    template = _template_dbname(base)
    worker = _worker_dbname(base)

    # A fresh clone every session; drop any stale leftover first so reruns start
    # from the migrated template, not a mutated previous run.
    if _database_exists(admin_url, worker):
        _run_maintenance(admin_url, sql.SQL("DROP DATABASE {}").format(sql.Identifier(worker)))
    _run_maintenance(
        admin_url,
        sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(worker), sql.Identifier(template)
        ),
    )
    return _with_dbname(base_url, worker)


# ---------------------------------------------------------------------------
# Core session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def worker_database_url() -> Generator[str, None, None]:
    """Provision this worker's isolated Postgres DB (migrated template clone).

    Session-scoped: created once per worker process. Yields the worker
    ``DATABASE_URL`` and drops the worker DB on teardown.
    """
    base_url = get_settings().database_url
    template_url = _migrate_template(base_url)
    worker_url = _clone_worker_db(base_url, template_url)
    yield worker_url

    admin_url = _admin_url(base_url)
    worker = _worker_dbname(_base_dbname(base_url))
    if _database_exists(admin_url, worker):
        _run_maintenance(admin_url, sql.SQL("DROP DATABASE {}").format(sql.Identifier(worker)))


@pytest.fixture(scope="session")
def db_path(worker_database_url: str) -> str:
    """Backward-compatible alias.

    The historical fixture name is ``db_path`` (a SQLite file path). It now
    yields the worker ``DATABASE_URL`` so existing fixtures that depend on
    ``db_path`` keep resolving; their bodies still need the ``?``->``%s`` /
    ``datetime('now')`` port (Task 6.3) but the plumbing is unchanged.
    """
    return worker_database_url


@pytest.fixture(scope="session")
def app(worker_database_url: str):
    """Session-scoped FastAPI app bound to this worker's Postgres DB.

    Points ``DATABASE_URL`` at the worker database, opens the psycopg pool via
    ``init_db`` (the single chokepoint), and builds the app with
    ``FakeSessionMiddleware`` swapped in for the real ``SessionMiddleware``.
    Session-scoped so the pool is opened once per worker; ``_clean_tables``
    handles per-test reset.
    """
    from app.database import close_db, init_db

    os.environ["DATABASE_URL"] = worker_database_url
    os.environ["ADMIN_API_KEY"] = ADMIN_API_KEY
    get_settings.cache_clear()
    init_db(worker_database_url)

    from app.main import create_app

    test_app = create_app()
    _install_fake_session_middleware(test_app)
    yield test_app

    close_db()
    get_settings.cache_clear()


@pytest.fixture()
def service_db(app) -> Generator[psycopg.Connection, None, None]:
    """A pooled ``dict_row`` connection against the worker DB for service tests.

    Replaces the SQLite ``db`` / ``service_db`` fixtures that handed back a raw
    ``sqlite3.Connection`` with ``row_factory=sqlite3.Row`` and
    ``PRAGMA foreign_keys=ON``. Under Postgres FK enforcement is always on, so no
    PRAGMA; keyed row access comes from the pool's ``dict_row`` factory
    (Decision 15).

    **Function-scoped, not session-scoped.** A session-scoped connection would
    hold its transaction (and row locks) open across tests, and the next test's
    autouse ``_clean_tables`` ``TRUNCATE`` (which needs ACCESS EXCLUSIVE) would
    block on it forever. A fresh pooled connection per test is committed and
    returned to the pool at test end, so truncation never contends.
    """
    from app.database import get_db

    with get_db() as conn:
        yield conn


@pytest.fixture()
def db(service_db: psycopg.Connection) -> psycopg.Connection:
    """Alias for ``service_db`` — the historical raw-connection fixture name."""
    return service_db


# ---------------------------------------------------------------------------
# Shared test-data helpers (Task 6.3)
# ---------------------------------------------------------------------------
#
# These consolidate the per-file ``seed_products`` copies and inline
# ``INSERT INTO sessions`` snippets that used to live in ``test_cart_routes.py``,
# ``tests/realapp/test_integration.py`` and ``tests/realapp/test_delivery_checkout.py``.
# They take a pooled ``dict_row`` psycopg connection (NOT a ``sqlite3.Connection``):
# ``?`` -> ``%s``, ``datetime('now')`` -> ``CURRENT_TIMESTAMP``, no
# ``PRAGMA foreign_keys`` (always on under Postgres). The caller owns commit —
# under ``with get_db() as conn:`` the chokepoint commits on exit.

# Default product catalog used across cart/integration route tests. Tuple shape:
# (id, name_en, price_cents, stock, is_active).
DEFAULT_PRODUCTS: tuple[tuple[str, str, int, int, bool], ...] = (
    ("lavender-dream", "Lavender Dream", 2500, 10, True),
    ("rose-garden", "Rose Garden", 1800, 5, True),
    ("midnight-musk", "Midnight Musk", 3200, 0, True),  # Out of stock
    ("winter-pine", "Winter Pine", 2000, 8, False),  # Inactive
    ("ocean-breeze", "Ocean Breeze", 1500, 20, True),
)


def seed_products(
    conn: psycopg.Connection,
    products: tuple[tuple[str, str, int, int, bool], ...] = DEFAULT_PRODUCTS,
) -> None:
    """Insert product rows via a pooled connection.

    Each tuple is ``(id, name_en, price_cents, stock, is_active)``. Timestamps
    default to ``CURRENT_TIMESTAMP`` server-side. ``is_active`` is stored as an
    integer column (0/1), so the ``bool`` is coerced to ``int`` on insert.
    """
    for pid, name, price, stock, active in products:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, "
            "is_active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (pid, name, price, stock, int(active)),
        )


def make_session(
    conn: psycopg.Connection,
    session_id: str,
    *,
    ttl: timedelta = timedelta(days=30),
) -> str:
    """Insert a session row via a pooled connection; return its id.

    Replaces the inline ``INSERT INTO sessions ... strftime(_DT_FMT)`` snippets:
    ``?`` -> ``%s`` and native ``datetime`` values instead of formatted strings
    (psycopg adapts ``datetime`` to ``timestamptz`` directly).
    """
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (%s, %s, %s)",
        (session_id, now, now + ttl),
    )
    return session_id


def add_cart_item(
    conn: psycopg.Connection, session_id: str, product_id: str, quantity: int
) -> None:
    """Insert a cart_items row via a pooled connection."""
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
        (session_id, product_id, quantity),
    )


# ---------------------------------------------------------------------------
# Per-test cleanup (autouse)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _volatile_tables(worker_database_url: str) -> list[str]:
    """Resolve the volatile-table allowlist once per worker.

    Curated allowlist = every base table in ``public`` MINUS the migration-seed
    tables and ``alembic_version``. Reading the live catalog (rather than a hand
    list) keeps the set correct as new tables land, while the explicit
    ``_NEVER_TRUNCATE`` exclusion preserves the "never truncate seed tables"
    guarantee.
    """
    with psycopg.connect(worker_database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            """
        ).fetchall()
    return [r["tablename"] for r in rows if r["tablename"] not in _NEVER_TRUNCATE]


def _insert_fake_session(conn: psycopg.Connection) -> None:
    """(Re)insert the FakeSessionMiddleware fake-session row after truncation."""
    now = datetime.now(UTC)
    conn.execute(
        """
        INSERT INTO sessions (id, created_at, expires_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (FAKE_SESSION_ID, now, now + timedelta(days=30)),
    )


@pytest.fixture(autouse=True)
def _clean_tables(
    worker_database_url: str, _volatile_tables: list[str]
) -> Generator[None, None, None]:
    """Reset volatile tables between tests (Decision 15).

    ``TRUNCATE <volatile tables> RESTART IDENTITY CASCADE``: ``CASCADE`` handles
    FK ordering, ``RESTART IDENTITY`` resets identity sequences so id-sensitive
    assertions stay stable. Seed tables are excluded (their rows persist from the
    template clone). The fake-session row is re-inserted afterwards because
    ``sessions`` is volatile.
    """
    with psycopg.connect(worker_database_url, autocommit=True) as conn:
        if _volatile_tables:
            conn.execute(
                sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(sql.Identifier(t) for t in _volatile_tables)
                )
            )
        _insert_fake_session(conn)
    yield


# ---------------------------------------------------------------------------
# HTTP clients (function-scoped — cheap, and header state must not leak)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client bound to the worker-DB app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client carrying the admin Bearer API key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"
        yield c


# ---------------------------------------------------------------------------
# Session / auth fixtures (consumed by test_auth.py and other route tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_id(app) -> str:
    """Return the fake session ID stamped by ``FakeSessionMiddleware``.

    The row exists in the DB (re-inserted each test by ``_clean_tables``), so
    tests that need a session_id for OAuth state, DB lookups, etc. get the same
    ID the middleware stamps on every request. Replaces the SQLite-era
    ``app._test_session_id`` random UUID with the stable ``FAKE_SESSION_ID``.
    """
    return FAKE_SESSION_ID


@pytest.fixture()
async def auth_client(app, session_id) -> AsyncGenerator[AsyncClient, None]:
    """Async client with the fake-session cookie pre-set.

    ``FakeSessionMiddleware`` ignores the cookie and pins ``FAKE_SESSION_ID``, but
    OAuth-callback tests read the cookie value directly, so it is set to match.
    """
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(settings.session_cookie_name, session_id)
        yield c
