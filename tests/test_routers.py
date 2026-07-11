"""Tests for route authentication and authorization."""

import pytest

from app.config import get_settings

ADMIN_ROUTES = [
    ("GET", "/v1/admin/orders"),
    ("POST", "/v1/admin/products/import"),
    ("POST", "/v1/admin/products"),
    ("GET", "/v1/admin/products"),
    ("GET", "/v1/admin/products/some-id"),
    ("PUT", "/v1/admin/products/some-id"),
    ("DELETE", "/v1/admin/products/some-id"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
async def test_admin_routes_reject_unauthenticated(client, method, path):
    """Admin routes reject unauthenticated access with 401."""
    response = await client.request(method, path)

    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_me_returns_401_when_not_authenticated(client):
    """GET /v1/auth/me returns 401 when no JWT cookie is present."""
    response = await client.get("/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_auth_logout_succeeds_when_anonymous(client):
    """POST /v1/auth/logout is safe to call even when not logged in."""
    response = await client.post("/v1/auth/logout")
    assert response.status_code == 200


@pytest.fixture()
def _unconfigure_oauth(monkeypatch, app):
    """Ensure OAuth is NOT configured for this test."""
    get_settings.cache_clear()
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_unconfigure_oauth")
async def test_auth_login_returns_503_without_oauth(client):
    """GET /v1/auth/login returns 503 when OAuth is NOT configured."""
    response = await client.get(
        "/v1/auth/login", params={"redirect_to": "/"}, follow_redirects=False
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "AUTH_NOT_CONFIGURED"
