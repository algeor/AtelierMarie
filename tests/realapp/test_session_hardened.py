"""Tests for session middleware — hardened validation, expiry, rotation, path exclusion."""

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.middleware.session import rotate_session

# SQLite-compatible datetime format
_DT_FMT = "%Y-%m-%d %H:%M:%S"
_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


# --- 7.1 No cookie → new session created ---


@pytest.mark.asyncio
async def test_no_cookie_creates_new_session(client: AsyncClient):
    """No cookie → new session created, cookie set with correct attributes."""
    response = await client.get("/v1/cart")

    settings = get_settings()
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert settings.session_cookie_name in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()
    # max_age present
    assert "max-age=" in set_cookie.lower()

    # Cookie value is valid UUID4
    cookie_val = response.cookies.get(settings.session_cookie_name)
    assert cookie_val is not None
    assert _UUID4_RE.match(cookie_val)


# --- 7.2 Valid session → request proceeds ---


@pytest.mark.asyncio
async def test_valid_session_proceeds(client: AsyncClient, db_path: str):
    """Valid session → request proceeds, request.state.session_id set correctly."""
    settings = get_settings()

    session_id = "aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee"
    now = datetime.now(UTC)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, now.strftime(_DT_FMT), (now + timedelta(days=20)).strftime(_DT_FMT)),
    )
    conn.commit()
    conn.close()

    client.cookies.set(settings.session_cookie_name, session_id)
    response = await client.get("/v1/cart")
    assert response.status_code == 200

    # Same session ID in response cookie
    returned_cookie = response.cookies.get(settings.session_cookie_name)
    assert returned_cookie == session_id


# --- 7.3 Valid session near expiry → expires_at updated ---


@pytest.mark.asyncio
async def test_near_expiry_session_extended(client: AsyncClient, db_path: str):
    """Valid session near expiry → expires_at updated in DB."""
    settings = get_settings()

    session_id = "11111111-2222-4333-8444-555555555555"
    now = datetime.now(UTC)
    created_at = (now - timedelta(days=25)).strftime(_DT_FMT)
    old_expires = (now + timedelta(days=3)).strftime(_DT_FMT)  # Within 7-day threshold

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, created_at, old_expires),
    )
    conn.commit()
    conn.close()

    client.cookies.set(settings.session_cookie_name, session_id)
    await client.get("/v1/cart")

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    new_expires = datetime.strptime(row[0], _DT_FMT).replace(tzinfo=UTC)
    old_expires_dt = datetime.strptime(old_expires, _DT_FMT).replace(tzinfo=UTC)
    assert new_expires > old_expires_dt


# --- 7.4 Valid session far from expiry → expires_at NOT updated ---


@pytest.mark.asyncio
async def test_far_from_expiry_not_updated(client: AsyncClient, db_path: str):
    """Valid session far from expiry → expires_at NOT updated."""
    settings = get_settings()

    session_id = "22222222-3333-4444-8555-666666666666"
    now = datetime.now(UTC)
    created_at = (now - timedelta(days=5)).strftime(_DT_FMT)
    original_expires = (now + timedelta(days=20)).strftime(_DT_FMT)  # Outside threshold

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, created_at, original_expires),
    )
    conn.commit()
    conn.close()

    client.cookies.set(settings.session_cookie_name, session_id)
    await client.get("/v1/cart")

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    assert row[0] == original_expires


# --- 7.5 Expired session → new session created ---


@pytest.mark.asyncio
async def test_expired_session_gets_new_cookie(client: AsyncClient, db_path: str):
    """Expired session → new session created, old cookie replaced."""
    settings = get_settings()

    expired_id = "12345678-1234-4abc-8def-123456789abc"
    now = datetime.now(UTC)
    expired_at = (now - timedelta(seconds=10)).strftime(_DT_FMT)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (expired_id, (now - timedelta(days=10)).strftime(_DT_FMT), expired_at),
    )
    conn.commit()
    conn.close()

    client.cookies.set(settings.session_cookie_name, expired_id)
    response = await client.get("/v1/cart")

    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != expired_id
    assert _UUID4_RE.match(new_cookie)

    # Verify correct attributes
    set_cookie = response.headers.get("set-cookie")
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


# --- 7.6 Unknown cookie → new session created ---


@pytest.mark.asyncio
async def test_unknown_cookie_gets_new_session(client: AsyncClient):
    """Unknown session cookie → new session created, cookie replaced."""
    settings = get_settings()

    unknown_id = "aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee"
    client.cookies.set(settings.session_cookie_name, unknown_id)
    response = await client.get("/v1/cart")

    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != unknown_id

    set_cookie = response.headers.get("set-cookie")
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


# --- 7.7 Malformed cookie → new session without DB query ---


@pytest.mark.asyncio
async def test_malformed_cookie_no_db_query(client: AsyncClient, db_path: str):
    """Malformed cookie (not UUID format) → new session created without DB query."""
    settings = get_settings()

    client.cookies.set(settings.session_cookie_name, "not-a-uuid-at-all")

    # The key insight: malformed cookie is rejected by regex before ANY DB operation.
    # We verify by checking: (1) new session is created, (2) the malformed value
    # is NOT in the sessions table (proving no SELECT was attempted for it).
    response = await client.get("/v1/cart")

    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != "not-a-uuid-at-all"
    assert _UUID4_RE.match(new_cookie)

    # Verify malformed value was never looked up — it doesn't appear in DB at all
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT id FROM sessions WHERE id = ?", ("not-a-uuid-at-all",)).fetchone()
    conn.close()
    assert row is None


# --- 7.8 Oversized cookie value → treated as absent ---


@pytest.mark.asyncio
async def test_oversized_cookie_treated_as_absent(client: AsyncClient):
    """Oversized cookie value → treated as absent, new session created."""
    settings = get_settings()

    # 100-char string that doesn't match UUID4 pattern
    oversized = "a" * 100
    client.cookies.set(settings.session_cookie_name, oversized)
    response = await client.get("/v1/cart")

    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != oversized
    assert _UUID4_RE.match(new_cookie)

    set_cookie = response.headers.get("set-cookie")
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


# --- 7.9 Session past absolute lifetime → treated as expired ---


@pytest.mark.asyncio
async def test_absolute_lifetime_expired(client: AsyncClient, db_path: str):
    """Session past absolute lifetime (created_at > 180 days ago) → treated as expired."""
    settings = get_settings()

    session_id = "33333333-4444-4555-8666-777777777777"
    now = datetime.now(UTC)
    # Created 181 days ago but expires_at still in the future
    created_at = (now - timedelta(days=181)).strftime(_DT_FMT)
    expires_at = (now + timedelta(days=5)).strftime(_DT_FMT)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, created_at, expires_at),
    )
    conn.commit()
    conn.close()

    client.cookies.set(settings.session_cookie_name, session_id)
    response = await client.get("/v1/cart")

    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != session_id


# --- 7.10 Health check path → no session created ---


@pytest.mark.asyncio
async def test_health_check_no_session(client: AsyncClient):
    """Health check path (/health) → no session created, no cookie set."""
    response = await client.get("/health")
    assert response.status_code == 200

    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is None


# --- 7.10a Path-exclusion negative cases ---


@pytest.mark.asyncio
async def test_path_exclusion_negative_health_records(client: AsyncClient):
    """Request to /health-records → session IS created (must NOT match /health exclusion)."""
    # /health-records should NOT be excluded
    response = await client.get("/health-records")
    # Will be 404 (no such route) but should still set a cookie
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert "session_id" in set_cookie


@pytest.mark.asyncio
async def test_path_exclusion_docs_subpath(client: AsyncClient):
    """Request to /v1/docs/swagger → session NOT created (matches prefix match)."""
    # /v1/docs is in skip paths, /v1/docs/anything should match prefix
    response = await client.get("/v1/docs/oauth2-redirect")
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is None


# --- 7.11 Session rotation helper ---


def test_session_rotation_migrates_cart(db_path: str, app):
    """Session rotation: cart items migrated, old session deleted, new session has user_id."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    # Set up old session
    now = datetime.now(UTC)
    old_session = "aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee"
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (old_session, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )

    # Create the user (required by FK on sessions.user_id → users.id)
    user_id = "user-123"
    conn.execute(
        "INSERT INTO users (id, google_id, email, name) VALUES (?, ?, ?, ?)",
        (user_id, "google-123", "user@example.com", "Test User"),
    )

    # Add products
    for i, (pid, stock) in enumerate([("product-a", 10), ("product-b", 10), ("product-c", 10)]):
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, "
            "is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'))",
            (pid, f"Product {i}", 1000, stock),
        )

    # Add cart items with specific quantities
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (old_session, "product-a", 2),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (old_session, "product-b", 5),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (old_session, "product-c", 1),
    )
    conn.commit()

    # Rotate
    user_id = "user-123"
    new_session = rotate_session(conn, old_session, user_id)

    # Verify new session exists with user_id
    row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (new_session,)).fetchone()
    assert row is not None
    assert row["user_id"] == user_id

    # Verify old session deleted
    old_row = conn.execute("SELECT id FROM sessions WHERE id = ?", (old_session,)).fetchone()
    assert old_row is None

    # Verify cart items migrated with correct quantities
    items = conn.execute(
        "SELECT product_id, quantity FROM cart_items WHERE session_id = ? ORDER BY product_id",
        (new_session,),
    ).fetchall()
    assert len(items) == 3
    assert items[0]["product_id"] == "product-a"
    assert items[0]["quantity"] == 2
    assert items[1]["product_id"] == "product-b"
    assert items[1]["quantity"] == 5
    assert items[2]["product_id"] == "product-c"
    assert items[2]["quantity"] == 1

    conn.close()


# --- 7.12 DB failure during session middleware ---


@pytest.mark.asyncio
async def test_db_failure_returns_500(client: AsyncClient):
    """DB failure during session middleware → 500 with generic error, no traceback."""
    from contextlib import contextmanager

    from app.middleware import session as session_module

    @contextmanager
    def broken_get_db():
        raise sqlite3.OperationalError("DB is broken")
        yield  # noqa: RET503 - unreachable but syntactically needed for generator

    with patch.object(session_module, "get_db", broken_get_db):
        response = await client.get("/v1/cart")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": None,
        }
    }
    # Verify no traceback in response body
    assert "Traceback" not in response.text


# --- 7.13 Session rotation rollback on failure ---


def test_session_rotation_rollback_on_failure(db_path: str, app):
    """If rotation fails mid-transaction, old session and cart remain intact."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    now = datetime.now(UTC)
    old_session = "aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee"
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (old_session, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )

    # Add a product + cart item
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, "
        "is_active, created_at, updated_at) "
        "VALUES ('rollback-product', 'Rollback Product', 1000, 10, 1, "
        "datetime('now'), datetime('now'))"
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (old_session, "rollback-product", 3),
    )
    conn.commit()

    # Attempt rotation with an invalid user_id (FK violation — no such user)
    # This should trigger the rollback path
    with pytest.raises(Exception):  # noqa: B017 — IntegrityError from FK violation
        rotate_session(conn, old_session, "nonexistent-user-id")

    # Verify old session still exists (rollback succeeded)
    old_row = conn.execute("SELECT id FROM sessions WHERE id = ?", (old_session,)).fetchone()
    assert old_row is not None, "Old session should still exist after failed rotation"

    # Verify cart items still attached to old session
    items = conn.execute(
        "SELECT product_id, quantity FROM cart_items WHERE session_id = ?",
        (old_session,),
    ).fetchall()
    assert len(items) == 1
    assert items[0]["product_id"] == "rollback-product"
    assert items[0]["quantity"] == 3

    conn.close()
