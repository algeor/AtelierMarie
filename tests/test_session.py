"""Tests for session cookie middleware."""

import sqlite3

import pytest
from httpx import AsyncClient

from app.config import get_settings


@pytest.mark.asyncio
async def test_new_visitor_gets_session_cookie(client: AsyncClient):
    """A request without a session cookie gets one set in the response."""
    response = await client.get("/v1/health")
    assert response.status_code == 200

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

    response = await client.get("/v1/health")
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
    """A request with a valid session cookie does not get a new one."""
    settings = get_settings()

    # First request — get a session
    first_response = await client.get("/v1/health")
    session_cookie = first_response.cookies.get(settings.session_cookie_name)
    assert session_cookie is not None

    # Second request — send the cookie back
    client.cookies.set(settings.session_cookie_name, session_cookie)
    second_response = await client.get("/v1/health")

    # Should NOT set a new cookie
    set_cookie = second_response.headers.get("set-cookie")
    assert set_cookie is None
