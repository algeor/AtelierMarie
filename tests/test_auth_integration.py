"""Integration tests for auth flow — smoke test, JWT cookie attributes, CORS.

Uses real middleware (tests/realapp/ pattern) to verify the full request chain.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import init_db
from app.services import auth_service

# --- Fixtures with real middleware ---

_TEST_COOKIE_DOMAIN = "test.local"


def _set_client_cookie(client: AsyncClient, name: str, value: str) -> None:
    """Set cookies for httpx's ASGI test host without creating duplicates."""
    client.cookies.set(name, value, domain=_TEST_COOKIE_DOMAIN, path="/")


# NOTE: there is no file-local ``db_path`` fixture. The tests below take
# ``db_path`` only for ordering; they inherit the root conftest's session-scoped
# ``db_path`` shim (which yields this worker's ``DATABASE_URL``). Defining a
# local module-scoped ``db_path`` here would shadow the root session-scoped
# fixtures and reintroduce the SQLite ``init_db(<path>)`` collision that the
# Decision 15 consolidation removed.


@pytest.fixture(scope="module")
def app(worker_database_url: str, monkeypatch_module):
    """Create app with REAL ``SessionMiddleware`` (no FakeSessionMiddleware swap).

    Mirrors the already-ported ``tests/realapp/conftest.py`` app fixture: binds
    ``DATABASE_URL`` to this worker's Postgres DB (from the root conftest), opens
    the psycopg pool via ``init_db(url)`` — the single chokepoint — and keeps the
    Google/CORS/ADMIN_API_KEY env this file's auth-flow tests need. It does NOT
    install ``FakeSessionMiddleware``: these tests deliberately exercise the real
    session chain (the ``tests/realapp`` pattern living under ``tests/``).
    """
    monkeypatch_module.setenv("DATABASE_URL", worker_database_url)
    monkeypatch_module.setenv("ADMIN_API_KEY", "integration-test-admin-key-1234")
    monkeypatch_module.setenv("GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch_module.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch_module.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/v1/auth/callback")
    monkeypatch_module.setenv("FRONTEND_URL", "http://localhost:3000")
    monkeypatch_module.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

    get_settings.cache_clear()
    init_db(worker_database_url)

    from app.main import create_app

    test_app = create_app()
    yield test_app
    # Do NOT close_db() here. ``_pool`` is a process-global owned by the
    # root conftest's session-scoped ``app`` fixture (one pool per xdist
    # worker). This module's ``app`` is module-scoped, so its teardown fires
    # mid-session while other ``tests/`` modules still need the pool; calling
    # close_db() would null the shared pool and every later test on this
    # worker would raise "Database pool is not initialized". The root
    # session-scoped teardown closes the pool at worker-session end.
    get_settings.cache_clear()


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# Per-test isolation is handled by the root conftest's autouse ``_clean_tables``
# (TRUNCATE of volatile tables). The former file-local ``_clean`` fixture (a raw
# sqlite3 ``DELETE FROM {table}`` loop over order_items/orders/cart_items/
# sessions/users) is removed: it was the SQLite-era equivalent of ``_clean_tables``
# and is now redundant under the Postgres template-clone harness.


# --- Task 70: Smoke test full OAuth flow ---


class TestOAuthSmokeTest:
    """Full flow: login → callback (mocked) → me(200) → logout → me(401)."""

    @pytest.mark.asyncio
    async def test_full_oauth_flow(self, client: AsyncClient, db_path):
        """End-to-end auth flow with mocked Google calls."""
        settings = get_settings()

        # Step 1: Hit login to get session cookie
        login_resp = await client.get("/v1/auth/login", follow_redirects=False)
        assert login_resp.status_code == 302

        # Extract session cookie from login response
        session_cookie = None
        for h in login_resp.headers.get_list("set-cookie"):
            if settings.session_cookie_name in h:
                session_cookie = h.split(";")[0].split("=", 1)[1]
                break
        assert session_cookie is not None

        # Extract state from redirect URL
        from urllib.parse import parse_qs, urlparse

        location = login_resp.headers["location"]
        state_token = parse_qs(urlparse(location).query)["state"][0]

        # Step 2: Simulate callback with mocked Google
        google_claims = {
            "sub": "google-smoke-user",
            "email": "smoke@test.com",
            "name": "Smoke User",
            "picture": None,
        }

        with (
            patch.object(
                auth_service, "exchange_code_for_tokens", new_callable=AsyncMock
            ) as mock_exchange,
            patch.object(
                auth_service, "verify_google_id_token", new_callable=AsyncMock
            ) as mock_verify,
        ):
            mock_exchange.return_value = "fake.id.token"
            mock_verify.return_value = google_claims

            _set_client_cookie(client, settings.session_cookie_name, session_cookie)
            callback_resp = await client.get(
                "/v1/auth/callback",
                params={"code": "auth-code", "state": state_token},
                follow_redirects=False,
            )

        assert callback_resp.status_code == 302
        assert "success=true" in callback_resp.headers["location"]

        # Extract JWT cookie from callback response
        jwt_cookie = None
        rotated_session_cookie = None
        for h in callback_resp.headers.get_list("set-cookie"):
            if settings.jwt_cookie_name in h:
                jwt_cookie = h.split(";")[0].split("=", 1)[1]
            if settings.session_cookie_name in h:
                rotated_session_cookie = h.split(";")[0].split("=", 1)[1]
            if jwt_cookie is not None and rotated_session_cookie is not None:
                break
        assert jwt_cookie is not None
        assert rotated_session_cookie is not None

        # Step 3: me(200) with JWT
        client.cookies.clear()
        _set_client_cookie(client, settings.session_cookie_name, rotated_session_cookie)
        _set_client_cookie(client, settings.jwt_cookie_name, jwt_cookie)
        me_resp = await client.get("/v1/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "smoke@test.com"

        # Step 4: logout
        logout_resp = await client.post("/v1/auth/logout")
        assert logout_resp.status_code == 200

        # Extract new session cookie (rotated)
        new_session = None
        for h in logout_resp.headers.get_list("set-cookie"):
            if settings.session_cookie_name in h and settings.jwt_cookie_name not in h:
                new_session = h.split(";")[0].split("=", 1)[1]
                break
        assert new_session is not None
        assert new_session != session_cookie  # Session was rotated

        # Verify X-Session-Rotated header
        assert logout_resp.headers.get("X-Session-Rotated") == "true"

        # Step 5: me(401) after logout — JWT cookie was cleared
        # Clear cookies and use new session
        client.cookies.clear()
        _set_client_cookie(client, settings.session_cookie_name, new_session)
        me_after_resp = await client.get("/v1/auth/me")
        assert me_after_resp.status_code == 401


# --- Task 71: JWT cookie attributes ---


class TestJwtCookieAttributes:
    """Verify JWT cookie has correct security attributes."""

    @pytest.mark.asyncio
    async def test_jwt_cookie_attributes_after_login(self, client: AsyncClient, db_path):
        """After login, atelier_auth cookie has HttpOnly, SameSite=Lax, Path=/."""
        settings = get_settings()

        # Get session first
        resp = await client.get("/v1/auth/login", follow_redirects=False)
        session_cookie = None
        for h in resp.headers.get_list("set-cookie"):
            if settings.session_cookie_name in h:
                session_cookie = h.split(";")[0].split("=", 1)[1]
                break

        from urllib.parse import parse_qs, urlparse

        state_token = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]

        with (
            patch.object(
                auth_service,
                "exchange_code_for_tokens",
                new_callable=AsyncMock,
                return_value="fake.id.token",
            ),
            patch.object(
                auth_service,
                "verify_google_id_token",
                new_callable=AsyncMock,
                return_value={
                    "sub": "google-cookie-test",
                    "email": "cookie@test.com",
                    "name": "Cookie",
                    "picture": None,
                },
            ),
        ):
            _set_client_cookie(client, settings.session_cookie_name, session_cookie)
            callback_resp = await client.get(
                "/v1/auth/callback",
                params={"code": "code", "state": state_token},
                follow_redirects=False,
            )

        # Find the JWT cookie header
        jwt_cookie_header = None
        for h in callback_resp.headers.get_list("set-cookie"):
            if settings.jwt_cookie_name in h and "max-age=0" not in h.lower():
                jwt_cookie_header = h.lower()
                break

        assert jwt_cookie_header is not None, "JWT cookie not found in response"
        assert "httponly" in jwt_cookie_header
        assert "samesite=lax" in jwt_cookie_header
        assert "path=/" in jwt_cookie_header
        # In development mode, Secure should be False (not present)
        # max-age should be 7 days = 604800 seconds
        assert "max-age=604800" in jwt_cookie_header


# --- Task 72: CORS config ---


class TestCorsConfig:
    """Verify CORS response headers for configured frontend origin."""

    @pytest.mark.asyncio
    async def test_cors_allows_credentials(self, client: AsyncClient):
        """Preflight returns Access-Control-Allow-Credentials: true."""
        response = await client.options(
            "/v1/products",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-credentials") == "true"

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origin(self, client: AsyncClient):
        """Response includes the allowed origin."""
        response = await client.options(
            "/v1/products",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_cors_allows_put_preflight(self, client: AsyncClient):
        """PUT admin endpoints pass browser CORS preflight."""
        response = await client.options(
            "/v1/admin/promotions/banner",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_cors_rejects_unknown_origin(self, client: AsyncClient):
        """Unknown origin does not get Access-Control-Allow-Origin."""
        response = await client.options(
            "/v1/products",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not have the evil origin
        assert response.headers.get("access-control-allow-origin") != "http://evil.com"
