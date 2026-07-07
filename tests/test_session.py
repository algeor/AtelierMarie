"""Tests for session cookie middleware."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.config import get_settings

# SQLite-compatible datetime format (matches middleware's _SQLITE_DT_FMT)
_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.mark.asyncio
async def test_new_visitor_gets_session_cookie(client: AsyncClient):
    """A request without a session cookie gets one set in the response."""
    response = await client.get("/v1/products")

    # Check Set-Cookie header
    settings = get_settings()
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert settings.session_cookie_name in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


@pytest.mark.asyncio
async def test_new_session_is_persisted_in_db(client: AsyncClient):
    """A new session cookie triggers an INSERT into the sessions table."""
    settings = get_settings()

    response = await client.get("/v1/products")
    session_id = response.cookies.get(settings.session_cookie_name)
    assert session_id is not None

    # Verify the row exists in the database
    from app.database import _db_path

    conn = sqlite3.connect(_db_path)
    row = conn.execute("SELECT id, expires_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == session_id
    assert row[1] is not None  # expires_at was set


@pytest.mark.asyncio
async def test_existing_session_is_preserved(client: AsyncClient):
    """A request with a valid session cookie keeps the same session ID.

    Per spec, Set-Cookie is sent on EVERY response (prevents timing side-channel),
    but the session ID value must remain the same for returning visitors.
    """
    settings = get_settings()

    # First request — get a session
    first_response = await client.get("/v1/products")
    session_cookie = first_response.cookies.get(settings.session_cookie_name)
    assert session_cookie is not None

    # Second request — send the cookie back
    client.cookies.set(settings.session_cookie_name, session_cookie)
    second_response = await client.get("/v1/products")

    # Set-Cookie IS present on every response (spec requirement)
    set_cookie = second_response.headers.get("set-cookie")
    assert set_cookie is not None

    # But the session ID must be the SAME — not a new session
    new_cookie = second_response.cookies.get(settings.session_cookie_name)
    assert new_cookie == session_cookie


@pytest.mark.asyncio
async def test_expired_session_gets_new_cookie(client: AsyncClient, db_path: str):
    """A request with an expired session cookie gets a fresh session."""
    settings = get_settings()

    # Insert an expired session directly into DB (valid UUID4 format)
    expired_id = "12345678-1234-4abc-8def-123456789abc"
    expired_at = (datetime.now(UTC) - timedelta(seconds=1)).strftime(_DT_FMT)
    now = datetime.now(UTC).strftime(_DT_FMT)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (expired_id, now, expired_at),
    )
    conn.commit()
    conn.close()

    # Send the expired session cookie
    client.cookies.set(settings.session_cookie_name, expired_id)
    response = await client.get("/v1/products")

    # Should issue a NEW session cookie (not reuse the expired one)
    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != expired_id


@pytest.mark.asyncio
async def test_invalid_uuid_cookie_gets_new_session(client: AsyncClient):
    """A request with a non-UUID cookie format gets a fresh session without DB lookup."""
    settings = get_settings()

    # Send a cookie that is not valid UUID4 format
    client.cookies.set(settings.session_cookie_name, "garbage-nonexistent-session-id")
    response = await client.get("/v1/products")

    # Should issue a NEW valid session cookie
    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != "garbage-nonexistent-session-id"
    # Verify the new cookie is a valid UUID4
    import re

    uuid4_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    assert uuid4_re.match(new_cookie)


@pytest.mark.asyncio
async def test_unknown_session_id_gets_new_cookie(client: AsyncClient):
    """A request with a valid UUID format but unknown session ID gets a fresh session."""
    settings = get_settings()

    # Send a valid UUID4 that doesn't exist in the DB
    unknown_uuid = "aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee"
    client.cookies.set(settings.session_cookie_name, unknown_uuid)
    response = await client.get("/v1/products")

    # Should issue a NEW session cookie
    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != unknown_uuid


@pytest.mark.asyncio
async def test_health_endpoint_skips_session(client: AsyncClient):
    """Health check endpoint does not create session cookies."""
    response = await client.get("/v1/health")
    assert response.status_code == 200

    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is None


@pytest.mark.asyncio
async def test_options_request_skips_session(client: AsyncClient):
    """OPTIONS pre-flight requests do not trigger session creation."""
    response = await client.options("/v1/products")

    # Should NOT set a session cookie
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is None


def test_cleanup_expired_sessions_removes_only_expired(db_path: str, app):
    """cleanup_expired_sessions deletes expired rows and leaves valid ones."""
    from app.database import cleanup_expired_sessions

    conn = sqlite3.connect(db_path)

    # Insert one expired and one valid session (SQLite-compatible format)
    past = (datetime.now(UTC) - timedelta(days=1)).strftime(_DT_FMT)
    future = (datetime.now(UTC) + timedelta(days=1)).strftime(_DT_FMT)
    conn.execute("INSERT INTO sessions (id, expires_at) VALUES (?, ?)", ("expired-1", past))
    conn.execute("INSERT INTO sessions (id, expires_at) VALUES (?, ?)", ("valid-1", future))
    conn.commit()
    conn.close()

    count = cleanup_expired_sessions()
    assert count == 1

    # Verify only the expired session was removed
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id FROM sessions").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "valid-1"


def test_cleanup_expired_sessions_empty_table(db_path: str, app):
    """cleanup_expired_sessions returns 0 when no sessions exist."""
    from app.database import cleanup_expired_sessions

    count = cleanup_expired_sessions()
    assert count == 0


@pytest.mark.asyncio
async def test_sliding_expiry_updates_within_threshold(client: AsyncClient, db_path: str):
    """When a session is within 7 days of expiring, its expiry gets extended."""
    settings = get_settings()

    # Insert a session that expires in 3 days (within 7-day threshold)
    session_id = "11111111-2222-4333-8444-555555555555"
    now = datetime.now(UTC)
    created_at = (now - timedelta(days=25)).strftime(_DT_FMT)
    expires_at = (now + timedelta(days=3)).strftime(_DT_FMT)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, created_at, expires_at),
    )
    conn.commit()
    conn.close()

    # Make a request with this session
    client.cookies.set(settings.session_cookie_name, session_id)
    await client.get("/v1/products")

    # Verify expires_at was extended
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    new_expires = datetime.strptime(row[0], _DT_FMT).replace(tzinfo=UTC)
    # Should now be ~30 days from now (not 3 days)
    assert new_expires > now + timedelta(days=25)


@pytest.mark.asyncio
async def test_sliding_expiry_no_update_when_far_from_expiry(client: AsyncClient, db_path: str):
    """When a session is far from expiring, its expiry is NOT updated."""
    settings = get_settings()

    # Insert a session that expires in 20 days (outside 7-day threshold)
    session_id = "22222222-3333-4444-8555-666666666666"
    now = datetime.now(UTC)
    created_at = (now - timedelta(days=10)).strftime(_DT_FMT)
    original_expires = (now + timedelta(days=20)).strftime(_DT_FMT)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, created_at, original_expires),
    )
    conn.commit()
    conn.close()

    # Make a request with this session
    client.cookies.set(settings.session_cookie_name, session_id)
    await client.get("/v1/products")

    # Verify expires_at was NOT changed
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    assert row[0] == original_expires


@pytest.mark.asyncio
async def test_absolute_lifetime_cap_rejects_old_session(client: AsyncClient, db_path: str):
    """A session older than 180 days is rejected even if expires_at is in the future."""
    settings = get_settings()

    # Insert a session created 181 days ago with a future expires_at
    session_id = "33333333-4444-4555-8666-777777777777"
    now = datetime.now(UTC)
    created_at = (now - timedelta(days=181)).strftime(_DT_FMT)
    expires_at = (now + timedelta(days=5)).strftime(_DT_FMT)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, created_at, expires_at),
    )
    conn.commit()
    conn.close()

    # Make a request with this session
    client.cookies.set(settings.session_cookie_name, session_id)
    response = await client.get("/v1/products")

    # Should get a NEW session (old one rejected)
    new_cookie = response.cookies.get(settings.session_cookie_name)
    assert new_cookie is not None
    assert new_cookie != session_id
