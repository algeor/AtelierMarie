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
        """POST /v1/auth/logout succeeds for anonymous sessions."""
        response = await client.post("/v1/auth/logout")
        assert response.status_code == 200
        # No X-Session-Rotated for anonymous (no user linked)
        assert "X-Session-Rotated" not in response.headers

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
    async def test_callback_invalid_state_redirects_with_error(self, client: AsyncClient):
        """GET /v1/auth/callback with invalid state redirects to frontend error."""
        response = await client.get(
            "/v1/auth/callback",
            params={"code": "fake-code", "state": "invalid-state"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers["location"]
        assert "error=invalid_state" in location

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
