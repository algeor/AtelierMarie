"""Tests for auth service and auth routes — Google OAuth flow."""

import sqlite3
import time
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.models.users import UserResponse
from app.services import auth_service

_DT_FMT = "%Y-%m-%d %H:%M:%S"


# --- Fixtures ---


@pytest.fixture()
def settings(app):
    """Return configured settings for the test app."""
    return get_settings()


@pytest.fixture()
def _configure_oauth(monkeypatch, app):
    """Configure OAuth settings for tests that need a valid OAuth config."""
    get_settings.cache_clear()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/v1/auth/callback")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def _unconfigure_oauth(monkeypatch, app):
    """Ensure OAuth is NOT configured for tests that expect 503."""
    get_settings.cache_clear()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def user_in_db(db_path) -> UserResponse:
    """Insert a test user and return the UserResponse."""
    user_id = "user-test-001"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, google_id, email, name, avatar_url, is_admin) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "google-123", "marie@example.com", "Marie", None, 1),
    )
    conn.commit()
    conn.close()
    return UserResponse(
        id=user_id, email="marie@example.com", name="Marie", avatar_url=None, is_admin=True
    )


@pytest.fixture()
def authenticated_session(db_path, session_id, user_in_db) -> str:
    """Link the session to the user. Returns session_id."""
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user_in_db.id, session_id))
    conn.commit()
    conn.close()
    return session_id


@pytest.fixture()
def jwt_cookie(authenticated_session, user_in_db, settings) -> str:
    """Create a valid JWT token for the test user."""
    return auth_service.create_jwt(user_in_db, authenticated_session)


# --- Unit Tests: validate_redirect_path ---


class TestValidateRedirectPath:
    def test_valid_path(self):
        assert auth_service.validate_redirect_path("/products") == "/products"

    def test_valid_root(self):
        assert auth_service.validate_redirect_path("/") == "/"

    def test_valid_with_query(self):
        assert auth_service.validate_redirect_path("/search?q=candle") == "/search?q=candle"

    def test_rejects_protocol_relative(self):
        assert auth_service.validate_redirect_path("//evil.com") == "/"

    def test_rejects_absolute_url(self):
        assert auth_service.validate_redirect_path("https://evil.com") == "/"

    def test_rejects_empty(self):
        assert auth_service.validate_redirect_path("") == "/"

    def test_rejects_none(self):
        assert auth_service.validate_redirect_path(None) == "/"

    def test_rejects_relative(self):
        assert auth_service.validate_redirect_path("relative/path") == "/"


# --- Unit Tests: JWT create/verify ---


class TestJwt:
    def test_create_and_verify_roundtrip(self, app, settings):
        user = UserResponse(id="u1", email="a@b.com", name="Test", avatar_url=None, is_admin=False)
        token = auth_service.create_jwt(user, "session-123")
        claims = auth_service.verify_jwt(token)

        assert claims is not None
        assert claims["user_id"] == "u1"
        assert claims["email"] == "a@b.com"
        assert claims["is_admin"] is False
        assert claims["session_id"] == "session-123"
        assert claims["iss"] == "atelier-marie"
        assert claims["aud"] == "atelier-marie-web"

    def test_expired_token_returns_none(self, app, settings):
        user = UserResponse(id="u1", email="a@b.com", name="Test", avatar_url=None, is_admin=False)
        # Create token with expired time
        payload = {
            "user_id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "session_id": "s1",
            "iss": "atelier-marie",
            "aud": "atelier-marie-web",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # expired 1 hour ago
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        assert auth_service.verify_jwt(token) is None

    def test_wrong_secret_returns_none(self, app, settings):
        user = UserResponse(id="u1", email="a@b.com", name="Test", avatar_url=None, is_admin=False)
        payload = {
            "user_id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "session_id": "s1",
            "iss": "atelier-marie",
            "aud": "atelier-marie-web",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        assert auth_service.verify_jwt(token) is None

    def test_wrong_issuer_returns_none(self, app, settings):
        payload = {
            "user_id": "u1",
            "email": "a@b.com",
            "is_admin": False,
            "session_id": "s1",
            "iss": "wrong-issuer",
            "aud": "atelier-marie-web",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        assert auth_service.verify_jwt(token) is None


# --- Unit Tests: OAuth State ---


class TestOAuthState:
    @pytest.mark.usefixtures("_configure_oauth")
    def test_build_google_auth_url_structure(self):
        url = auth_service.build_google_auth_url("session-abc", return_to="/products")

        assert "accounts.google.com" in url
        assert "client_id=test-client-id" in url
        assert "response_type=code" in url
        assert "scope=openid" in url
        assert "code_challenge_method=S256" in url
        assert "state=" in url

    @pytest.mark.usefixtures("_configure_oauth")
    def test_validate_state_success(self):
        url = auth_service.build_google_auth_url("session-xyz", return_to="/cart")

        # Extract state from URL
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        state_token = params["state"][0]

        claims = auth_service.validate_state(state_token, "session-xyz")
        assert claims["type"] == "oauth_state"
        assert claims["session_id"] == "session-xyz"
        assert claims["return_to"] == "/cart"
        assert "code_verifier" in claims

    @pytest.mark.usefixtures("_configure_oauth")
    def test_validate_state_wrong_session(self):
        url = auth_service.build_google_auth_url("session-original", return_to="/")
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        state_token = parse_qs(parsed.query)["state"][0]

        with pytest.raises(auth_service.InvalidStateError, match="Session ID mismatch"):
            auth_service.validate_state(state_token, "different-session")

    @pytest.mark.usefixtures("_configure_oauth")
    def test_validate_state_expired(self):
        settings = get_settings()
        payload = {
            "type": "oauth_state",
            "session_id": "s1",
            "nonce": "abc",
            "code_verifier": "cv",
            "return_to": "/",
            "iat": int(time.time()) - 700,
            "exp": int(time.time()) - 100,  # expired
        }
        state = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(auth_service.InvalidStateError):
            auth_service.validate_state(state, "s1")

    @pytest.mark.usefixtures("_configure_oauth")
    def test_validate_state_wrong_type(self):
        settings = get_settings()
        payload = {
            "type": "not_oauth_state",
            "session_id": "s1",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
        }
        state = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with pytest.raises(auth_service.InvalidStateError, match="Invalid state token type"):
            auth_service.validate_state(state, "s1")


# --- Unit Tests: upsert_user ---


class TestUpsertUser:
    def test_first_user_is_admin(self, db_path, app):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")

        user = auth_service.upsert_user(conn, "google-1", "first@test.com", "First", None)
        conn.close()

        assert user.is_admin is True
        assert user.email == "first@test.com"
        assert user.name == "First"

    def test_second_user_is_not_admin(self, db_path, app):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")

        auth_service.upsert_user(conn, "google-1", "first@test.com", "First", None)
        user2 = auth_service.upsert_user(conn, "google-2", "second@test.com", "Second", None)
        conn.close()

        assert user2.is_admin is False

    def test_returning_user_updated(self, db_path, app):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")

        user1 = auth_service.upsert_user(conn, "google-1", "a@test.com", "Old Name", None)
        user2 = auth_service.upsert_user(
            conn, "google-1", "a@test.com", "New Name", "http://avatar.jpg"
        )
        conn.close()

        assert user1.id == user2.id  # Same user
        assert user2.name == "New Name"
        assert user2.avatar_url == "http://avatar.jpg"
        assert user2.is_admin is True  # Still admin


# --- Route Integration Tests ---


class TestLoginRoute:
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_unconfigure_oauth")
    async def test_login_returns_503_without_config(self, client: AsyncClient):
        """GET /v1/auth/login returns 503 when OAuth is not configured."""
        response = await client.get("/v1/auth/login", follow_redirects=False)
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "AUTH_NOT_CONFIGURED"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_login_redirects_to_google(self, client: AsyncClient):
        """GET /v1/auth/login redirects to Google when configured."""
        response = await client.get(
            "/v1/auth/login", params={"redirect_to": "/products"}, follow_redirects=False
        )
        assert response.status_code == 302
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "client_id=test-client-id" in location
        assert "code_challenge" in location


class TestMeRoute:
    @pytest.mark.asyncio
    async def test_me_unauthorized_no_cookie(self, client: AsyncClient):
        """GET /v1/auth/me returns 401 without JWT cookie."""
        response = await client.get("/v1/auth/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"

    @pytest.mark.asyncio
    async def test_me_success_with_valid_jwt(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session, user_in_db
    ):
        """GET /v1/auth/me returns user when valid JWT cookie is present."""
        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        response = await auth_client.get("/v1/auth/me")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == user_in_db.id
        assert body["email"] == user_in_db.email
        assert body["is_admin"] is True

    @pytest.mark.asyncio
    async def test_me_rejects_expired_jwt(self, auth_client: AsyncClient, settings):
        """GET /v1/auth/me returns 401 for expired JWT."""
        payload = {
            "user_id": "u1",
            "email": "a@b.com",
            "is_admin": False,
            "session_id": "s1",
            "iss": "atelier-marie",
            "aud": "atelier-marie-web",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        auth_client.cookies.set(settings.jwt_cookie_name, expired_token)

        response = await auth_client.get("/v1/auth/me")
        assert response.status_code == 401


class TestLogoutRoute:
    @pytest.mark.asyncio
    async def test_logout_anonymous_session(self, client: AsyncClient):
        """POST /v1/auth/logout rotates an existing anonymous session."""
        response = await client.post("/v1/auth/logout")
        assert response.status_code == 200
        assert response.headers.get("X-Session-Rotated") == "true"

    @pytest.mark.asyncio
    async def test_logout_authenticated_rotates_session(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session
    ):
        """POST /v1/auth/logout clears JWT, rotates session, sets header."""
        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        response = await auth_client.post("/v1/auth/logout")

        assert response.status_code == 200
        assert response.headers.get("X-Session-Rotated") == "true"

        # JWT cookie should be cleared (max-age=0 or deleted)
        set_cookie_headers = response.headers.get_list("set-cookie")
        jwt_cleared = any(
            settings.jwt_cookie_name in h and ("max-age=0" in h.lower() or "expires=" in h.lower())
            for h in set_cookie_headers
        )
        assert jwt_cleared

    @pytest.mark.asyncio
    async def test_logout_unlinks_user_from_session(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session, db_path
    ):
        """POST /v1/auth/logout removes user_id from the old session."""
        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        await auth_client.post("/v1/auth/logout")

        # Verify old session has user_id=NULL
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE id = ?", (authenticated_session,)
        ).fetchone()
        conn.close()

        assert row["user_id"] is None


class TestCallbackRoute:
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_invalid_state_returns_400(self, client: AsyncClient):
        """GET /v1/auth/callback with invalid state returns 400."""
        response = await client.get(
            "/v1/auth/callback",
            params={"code": "fake-code", "state": "invalid-state"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_state"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_happy_path(self, auth_client: AsyncClient, session_id, db_path):
        """GET /v1/auth/callback with valid state completes the OAuth flow."""
        settings = get_settings()

        # Build a valid state token for this session
        url = auth_service.build_google_auth_url(session_id, return_to="/products")
        from urllib.parse import parse_qs, urlparse

        state_token = parse_qs(urlparse(url).query)["state"][0]

        # Mock the Google token exchange and ID token verification
        fake_id_token = "fake.id.token"
        google_claims = {
            "sub": "google-new-user",
            "email": "newuser@gmail.com",
            "name": "New User",
            "picture": "https://lh3.google.com/photo.jpg",
        }

        with (
            patch.object(
                auth_service, "exchange_code_for_tokens", new_callable=AsyncMock
            ) as mock_exchange,
            patch.object(
                auth_service, "verify_google_id_token", new_callable=AsyncMock
            ) as mock_verify,
        ):
            mock_exchange.return_value = fake_id_token
            mock_verify.return_value = google_claims

            response = await auth_client.get(
                "/v1/auth/callback",
                params={"code": "auth-code-123", "state": state_token},
                follow_redirects=False,
            )

        assert response.status_code == 302
        location = response.headers["location"]
        assert "success=true" in location
        assert "redirect_to=/products" in location

        # JWT cookie should be set
        set_cookie_headers = response.headers.get_list("set-cookie")
        has_jwt_cookie = any(settings.jwt_cookie_name in h for h in set_cookie_headers)
        assert has_jwt_cookie

        # User should be created in DB
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        user_row = conn.execute(
            "SELECT * FROM users WHERE google_id = ?", ("google-new-user",)
        ).fetchone()
        conn.close()

        assert user_row is not None
        assert user_row["email"] == "newuser@gmail.com"
        assert user_row["is_admin"] == 1  # First user is admin

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_token_exchange_failure(self, auth_client: AsyncClient, session_id):
        """Mock Google token endpoint error → verify 400 with token_exchange_failed."""
        url = auth_service.build_google_auth_url(session_id, return_to="/")
        from urllib.parse import parse_qs, urlparse

        state_token = parse_qs(urlparse(url).query)["state"][0]

        with patch.object(
            auth_service,
            "exchange_code_for_tokens",
            new_callable=AsyncMock,
            side_effect=auth_service.TokenExchangeError("Google returned 400"),
        ):
            response = await auth_client.get(
                "/v1/auth/callback",
                params={"code": "bad-code", "state": state_token},
                follow_redirects=False,
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "token_exchange_failed"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_email_not_verified(self, auth_client: AsyncClient, session_id):
        """Mock Google to return unverified email → verify redirect with error."""
        url = auth_service.build_google_auth_url(session_id, return_to="/")
        from urllib.parse import parse_qs, urlparse

        state_token = parse_qs(urlparse(url).query)["state"][0]

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
                side_effect=auth_service.EmailNotVerifiedError("Email not verified"),
            ),
        ):
            response = await auth_client.get(
                "/v1/auth/callback",
                params={"code": "auth-code", "state": state_token},
                follow_redirects=False,
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "email_not_verified"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_expired_state(self, auth_client: AsyncClient, session_id):
        """Expired state token → 400 invalid_state error."""
        settings = get_settings()
        payload = {
            "type": "oauth_state",
            "session_id": session_id,
            "nonce": "abc",
            "code_verifier": "cv",
            "return_to": "/",
            "iat": int(time.time()) - 700,
            "exp": int(time.time()) - 100,
        }
        expired_state = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        response = await auth_client.get(
            "/v1/auth/callback",
            params={"code": "code", "state": expired_state},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_state"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_tampered_state_signature(self, auth_client: AsyncClient, session_id):
        """State signed with wrong secret → 400 invalid_state error."""
        payload = {
            "type": "oauth_state",
            "session_id": session_id,
            "nonce": "abc",
            "code_verifier": "cv",
            "return_to": "/",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
        }
        tampered_state = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        response = await auth_client.get(
            "/v1/auth/callback",
            params={"code": "code", "state": tampered_state},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_state"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_mismatched_session_id(self, auth_client: AsyncClient, session_id):
        """State with different session_id → 400 invalid_state error."""
        settings = get_settings()
        payload = {
            "type": "oauth_state",
            "session_id": "different-session-id",
            "nonce": "abc",
            "code_verifier": "cv",
            "return_to": "/",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
        }
        mismatch_state = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        response = await auth_client.get(
            "/v1/auth/callback",
            params={"code": "code", "state": mismatch_state},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_state"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_missing_type_claim(self, auth_client: AsyncClient, session_id):
        """State without type=oauth_state → 400 invalid_state error."""
        settings = get_settings()
        payload = {
            "session_id": session_id,
            "nonce": "abc",
            "code_verifier": "cv",
            "return_to": "/",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
        }
        no_type_state = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        response = await auth_client.get(
            "/v1/auth/callback",
            params={"code": "code", "state": no_type_state},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_state"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_callback_links_session_and_backfills_orders(
        self, auth_client: AsyncClient, session_id, db_path
    ):
        """After callback: sessions.user_id set, anonymous orders backfilled."""
        # Insert an anonymous order for this session
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
            "VALUES (?, ?, 'pending', 5000, 'anon@example.com')",
            ("order-anon-1", session_id),
        )
        conn.commit()
        conn.close()

        url = auth_service.build_google_auth_url(session_id, return_to="/")
        from urllib.parse import parse_qs, urlparse

        state_token = parse_qs(urlparse(url).query)["state"][0]

        with (
            patch.object(
                auth_service, "exchange_code_for_tokens", new_callable=AsyncMock
            ) as mock_exchange,
            patch.object(
                auth_service, "verify_google_id_token", new_callable=AsyncMock
            ) as mock_verify,
        ):
            mock_exchange.return_value = "fake.id.token"
            mock_verify.return_value = {
                "sub": "google-backfill-user",
                "email": "backfill@test.com",
                "name": "Backfill User",
                "picture": None,
            }

            await auth_client.get(
                "/v1/auth/callback",
                params={"code": "code", "state": state_token},
                follow_redirects=False,
            )

        # Verify session linked and order backfilled
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        session_row = conn.execute(
            "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        order_row = conn.execute(
            "SELECT user_id FROM orders WHERE id = ?", ("order-anon-1",)
        ).fetchone()
        conn.close()

        assert session_row["user_id"] is not None
        assert order_row["user_id"] == session_row["user_id"]


class TestLogoutCartIsolation:
    """Test that logout doesn't transfer cart to new session."""

    @pytest.mark.asyncio
    async def test_logout_does_not_transfer_cart(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session, db_path
    ):
        """Add items, logout, verify new session has empty cart."""
        # Insert a cart item for the authenticated session
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            ("test-prod-cart", "Test", 1000, 10),
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (authenticated_session, "test-prod-cart", 2),
        )
        conn.commit()
        conn.close()

        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        response = await auth_client.post("/v1/auth/logout")
        assert response.status_code == 200

        # The new session cookie was set — extract it
        set_cookies = response.headers.get_list("set-cookie")
        new_session_cookie = None
        for h in set_cookies:
            if settings.session_cookie_name in h and settings.jwt_cookie_name not in h:
                # Parse session_id value from set-cookie header
                parts = h.split(";")[0]
                if "=" in parts:
                    new_session_cookie = parts.split("=", 1)[1]
                    break

        assert new_session_cookie is not None
        # Verify new session has no cart items
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        items = conn.execute(
            "SELECT * FROM cart_items WHERE session_id = ?", (new_session_cookie,)
        ).fetchall()
        conn.close()
        assert len(items) == 0


class TestJwtAdditional:
    """Additional JWT edge case tests."""

    def test_wrong_audience_returns_none(self, app, settings):
        """JWT with wrong audience is rejected."""
        payload = {
            "user_id": "u1",
            "email": "a@b.com",
            "is_admin": False,
            "session_id": "s1",
            "iss": "atelier-marie",
            "aud": "wrong-audience",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        assert auth_service.verify_jwt(token) is None

    def test_wrong_algorithm_returns_none(self, app, settings):
        """JWT signed with different algorithm is rejected."""
        payload = {
            "user_id": "u1",
            "email": "a@b.com",
            "is_admin": False,
            "session_id": "s1",
            "iss": "atelier-marie",
            "aud": "atelier-marie-web",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        # Sign with a different algorithm that verify_jwt doesn't accept
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS384")
        assert auth_service.verify_jwt(token) is None

    def test_rotated_secret_rejects_old_token(self, app, monkeypatch):
        """JWT signed with old secret rejected after secret rotation."""
        user = UserResponse(id="u1", email="a@b.com", name="T", avatar_url=None, is_admin=False)
        token = auth_service.create_jwt(user, "s1")

        # "Rotate" secret
        get_settings.cache_clear()
        monkeypatch.setenv("JWT_SECRET", "new-rotated-secret-key-here")
        get_settings.cache_clear()

        assert auth_service.verify_jwt(token) is None

        # Cleanup
        get_settings.cache_clear()


class TestMeRouteAdditional:
    """Additional /me edge cases."""

    @pytest.mark.asyncio
    async def test_me_fails_when_session_user_id_null(
        self, auth_client: AsyncClient, settings, session_id, db_path
    ):
        """If session user_id is NULL (post-logout), /me returns 401."""
        # Create a JWT referencing this session and user
        user = UserResponse(
            id="ghost-user", email="ghost@test.com", name="Ghost", avatar_url=None, is_admin=False
        )
        token = auth_service.create_jwt(user, session_id)

        # Session exists but user_id is NULL (not linked)
        auth_client.cookies.set(settings.jwt_cookie_name, token)
        response = await auth_client.get("/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_fails_when_jwt_session_claim_differs(
        self, auth_client: AsyncClient, settings, authenticated_session, user_in_db
    ):
        """A JWT for another session is not valid on the current request session."""
        token = auth_service.create_jwt(user_in_db, "different-session")
        auth_client.cookies.set(settings.jwt_cookie_name, token)

        response = await auth_client.get("/v1/auth/me")
        assert response.status_code == 401


class TestBuildGoogleAuthUrl:
    """Task 39: Verify build_google_auth_url generates valid state and URL."""

    @pytest.mark.usefixtures("_configure_oauth")
    def test_url_contains_required_params(self):
        url = auth_service.build_google_auth_url("session-test", return_to="/")
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["client_id"][0] == "test-client-id.apps.googleusercontent.com"
        assert params["redirect_uri"][0] == "http://localhost:8000/v1/auth/callback"
        assert params["response_type"][0] == "code"
        assert "openid" in params["scope"][0]
        assert "email" in params["scope"][0]
        assert "profile" in params["scope"][0]
        assert params["code_challenge_method"][0] == "S256"
        assert "code_challenge" in params
        assert "state" in params

    @pytest.mark.usefixtures("_configure_oauth")
    def test_state_token_has_type_claim(self):
        url = auth_service.build_google_auth_url("session-test", return_to="/checkout")
        from urllib.parse import parse_qs, urlparse

        state_token = parse_qs(urlparse(url).query)["state"][0]
        claims = auth_service.validate_state(state_token, "session-test")
        assert claims["type"] == "oauth_state"
        assert claims["return_to"] == "/checkout"


class TestVerifyGoogleIdToken:
    """Task 40: Test verify_google_id_token with mocked JWKS."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_rejects_token_without_kid(self):
        """Token header missing kid → IdTokenVerificationError."""
        # Create a token without kid in header
        token = jwt.encode(
            {"sub": "123", "email": "x@y.com"},
            "secret",
            algorithm="HS256",
        )
        with pytest.raises(auth_service.IdTokenVerificationError, match="No kid"):
            await auth_service.verify_google_id_token(token)

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_rejects_invalid_token_header(self):
        """Completely invalid token → IdTokenVerificationError."""
        with pytest.raises(auth_service.IdTokenVerificationError, match="Cannot decode"):
            await auth_service.verify_google_id_token("not.a.valid.jwt")


class TestJwksCache:
    """Task 52: JWKS cache behavior tests."""

    def test_cache_starts_empty_and_expired(self):
        """Fresh cache is empty and expired."""
        cache = auth_service._JwksCache()
        assert cache.is_empty is True
        assert cache.is_expired is True

    def test_cache_update_stores_keys(self):
        """After update, keys are retrievable."""
        cache = auth_service._JwksCache()
        jwks = {"keys": [{"kid": "key1", "kty": "RSA"}, {"kid": "key2", "kty": "RSA"}]}
        cache.update(jwks)

        assert cache.is_empty is False
        assert cache.get_key("key1") == {"kid": "key1", "kty": "RSA"}
        assert cache.get_key("key2") == {"kid": "key2", "kty": "RSA"}
        assert cache.get_key("key3") is None

    def test_cache_needs_refresh_for_unknown_kid(self):
        """Unknown kid triggers refresh even within TTL."""
        cache = auth_service._JwksCache()
        jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}
        cache.update(jwks)

        assert cache.needs_refresh("key1") is False
        assert cache.needs_refresh("unknown-kid") is True

    def test_cache_needs_refresh_after_ttl(self):
        """After TTL expires, all kids need refresh."""
        cache = auth_service._JwksCache()
        jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}
        cache.update(jwks)
        # Simulate TTL expiry
        cache._fetched_at = time.time() - (7 * 60 * 60)  # 7 hours ago

        assert cache.needs_refresh("key1") is True

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_fetch_jwks_uses_stale_cache_on_failure(self):
        """When fetch fails but cache has keys, uses stale cache."""
        import httpx

        # Pre-populate cache
        auth_service._jwks_cache.update({"keys": [{"kid": "stale-key", "kty": "RSA"}]})
        # Expire the cache
        auth_service._jwks_cache._fetched_at = 0

        # Mock httpx to fail
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Network down"))
            mock_client_cls.return_value = mock_client

            # Reset circuit breaker to allow request
            auth_service._google_oauth_breaker._failures.clear()
            auth_service._google_oauth_breaker._is_open = False

            await auth_service._fetch_jwks()

        # Stale key should still be available
        assert auth_service._jwks_cache.get_key("stale-key") is not None


class TestRequireAdmin:
    """Task 44: require_admin dependency with various credential combos."""

    @pytest.mark.asyncio
    async def test_admin_jwt_grants_access(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session
    ):
        """Admin JWT cookie → access granted."""
        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        # user_in_db is admin=True
        response = await auth_client.get("/v1/admin/dashboard")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logged_out_admin_jwt_rejected(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session
    ):
        """Logout/session rotation invalidates the old admin JWT for admin routes."""
        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        logout_response = await auth_client.post("/v1/auth/logout")
        assert logout_response.status_code == 200

        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        response = await auth_client.get("/v1/admin/dashboard")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_jwt_returns_403(
        self, auth_client: AsyncClient, settings, session_id, db_path
    ):
        """Non-admin JWT → 403 Forbidden (key cannot escalate)."""
        # Create non-admin user
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (id, google_id, email, name, is_admin) VALUES (?, ?, ?, ?, ?)",
            ("user-nonadmin", "google-nonadmin", "nonadmin@test.com", "NonAdmin", 0),
        )
        conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", ("user-nonadmin", session_id))
        conn.commit()
        conn.close()

        user = UserResponse(
            id="user-nonadmin",
            email="nonadmin@test.com",
            name="NonAdmin",
            avatar_url=None,
            is_admin=False,
        )
        token = auth_service.create_jwt(user, session_id)
        auth_client.cookies.set(settings.jwt_cookie_name, token)
        response = await auth_client.get("/v1/admin/dashboard")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_api_key_grants_access(self, app):
        """Valid Bearer API key → access granted (no JWT needed)."""
        from httpx import ASGITransport
        from httpx import AsyncClient as HttpxClient

        transport = ASGITransport(app=app)
        async with HttpxClient(transport=transport, base_url="http://test") as c:
            from conftest import ADMIN_API_KEY

            c.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"
            response = await c.get("/v1/admin/dashboard")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, app):
        """Invalid Bearer key → 401."""
        from httpx import ASGITransport
        from httpx import AsyncClient as HttpxClient

        transport = ASGITransport(app=app)
        async with HttpxClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer wrong-key"
            response = await c.get("/v1/admin/dashboard")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_no_credentials_returns_401(self, app):
        """No JWT, no API key → 401."""
        from httpx import ASGITransport
        from httpx import AsyncClient as HttpxClient

        transport = ASGITransport(app=app)
        async with HttpxClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/v1/admin/dashboard")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_api_key_config_denies_all(self, app, monkeypatch):
        """When admin_api_key is empty, API key auth disabled entirely."""
        from httpx import ASGITransport
        from httpx import AsyncClient as HttpxClient

        get_settings.cache_clear()
        monkeypatch.setenv("ADMIN_API_KEY", "")
        get_settings.cache_clear()

        transport = ASGITransport(app=app)
        async with HttpxClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer anything"
            response = await c.get("/v1/admin/dashboard")
            assert response.status_code == 401

        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_nonadmin_jwt_plus_valid_key_still_403(
        self, auth_client: AsyncClient, settings, session_id, db_path
    ):
        """Non-admin JWT + valid API key → 403 (JWT is identity, key cannot escalate)."""
        from conftest import ADMIN_API_KEY

        # Create non-admin user and link session
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (id, google_id, email, name, is_admin) VALUES (?, ?, ?, ?, ?)",
            ("user-na2", "google-na2", "na2@test.com", "NA", 0),
        )
        conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", ("user-na2", session_id))
        conn.commit()
        conn.close()

        user = UserResponse(
            id="user-na2", email="na2@test.com", name="NA", avatar_url=None, is_admin=False
        )
        token = auth_service.create_jwt(user, session_id)
        auth_client.cookies.set(settings.jwt_cookie_name, token)
        auth_client.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"

        response = await auth_client.get("/v1/admin/dashboard")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_jwt_with_invalid_key_succeeds_via_jwt(
        self, auth_client: AsyncClient, jwt_cookie, settings, authenticated_session
    ):
        """Admin JWT + invalid API key → succeeds via JWT (key ignored)."""
        auth_client.cookies.set(settings.jwt_cookie_name, jwt_cookie)
        auth_client.headers["Authorization"] = "Bearer wrong-key"
        response = await auth_client.get("/v1/admin/dashboard")
        assert response.status_code == 200


class TestReturnToValidation:
    """Task 55: return_to path validation through the login flow."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_valid_return_to_preserved(self, client: AsyncClient):
        """Valid path starting with / is preserved in redirect URL."""
        response = await client.get(
            "/v1/auth/login", params={"redirect_to": "/products/candle"}, follow_redirects=False
        )
        assert response.status_code == 302
        location = response.headers["location"]
        # Decode the state and verify return_to
        from urllib.parse import parse_qs, urlparse

        state = parse_qs(urlparse(location).query)["state"][0]
        settings = get_settings()
        payload = jwt.decode(
            state,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert payload["return_to"] == "/products/candle"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_configure_oauth")
    async def test_invalid_return_to_falls_back_to_root(self, client: AsyncClient):
        """Invalid path (contains //) falls back to /."""
        response = await client.get(
            "/v1/auth/login", params={"redirect_to": "//evil.com"}, follow_redirects=False
        )
        assert response.status_code == 302
        location = response.headers["location"]
        from urllib.parse import parse_qs, urlparse

        state = parse_qs(urlparse(location).query)["state"][0]
        settings = get_settings()
        payload = jwt.decode(
            state,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
        assert payload["return_to"] == "/"


class TestUpsertUserConcurrency:
    """Task 41: Test first-user-is-admin concurrency scenario."""

    def test_concurrent_upsert_exactly_one_admin(self, db_path, app):
        """Two threads call upsert_user simultaneously, only one gets admin."""
        import threading

        results = []
        barrier = threading.Barrier(2)

        def worker(google_id, email):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            barrier.wait()  # Start simultaneously
            try:
                user = auth_service.upsert_user(conn, google_id, email, "User", None)
                results.append(user)
            finally:
                conn.close()

        t1 = threading.Thread(target=worker, args=("g1", "a@test.com"))
        t2 = threading.Thread(target=worker, args=("g2", "b@test.com"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        admin_count = sum(1 for u in results if u.is_admin)
        assert admin_count == 1
