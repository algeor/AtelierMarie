"""Tests for stub routers — verify 501 responses with correct error shape."""

import pytest

STUB_ROUTES = [
    ("GET", "/v1/cart"),
    ("POST", "/v1/cart"),
    ("PATCH", "/v1/cart/some-id"),
    ("DELETE", "/v1/cart/some-id"),
    ("POST", "/v1/auth/google"),
    ("GET", "/v1/auth/me"),
]

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
@pytest.mark.parametrize("method,path", STUB_ROUTES)
async def test_stub_returns_501(client, method, path):
    response = await client.request(method, path)

    assert response.status_code == 501

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_IMPLEMENTED"
    assert isinstance(body["error"]["message"], str)
    assert "details" in body["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
async def test_admin_routes_reject_unauthenticated(client, method, path):
    """Admin routes reject unauthenticated access with 401."""
    response = await client.request(method, path)

    assert response.status_code == 401
    body = response.json()
    # Error envelope format: {"error": {"code": ..., "message": ...}}
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"
