"""Route tests for reaction endpoints."""

import pytest

from app.database import get_db


@pytest.fixture()
def active_product(db):
    """Insert an active product."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (%s, %s, %s, %s, %s)",
            ("test-candle", "Test Candle", 2500, 10, 1),
        )
    return "test-candle"


@pytest.fixture()
def inactive_product(db):
    """Insert an inactive product."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (%s, %s, %s, %s, %s)",
            ("inactive-candle", "Inactive Candle", 2500, 10, 0),
        )
    return "inactive-candle"


class TestToggleReactionRoute:
    """POST /v1/products/{product_id}/reactions"""

    async def test_toggle_on_returns_201(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["reaction_type"] == "heart"
        assert data["active"] is True

    async def test_toggle_off_returns_200(self, client, active_product):
        await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        resp = await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    async def test_product_not_found_404(self, client):
        resp = await client.post(
            "/v1/products/nonexistent/reactions",
            json={"reaction_type": "heart"},
        )
        assert resp.status_code == 404

    async def test_inactive_product_404(self, client, inactive_product):
        resp = await client.post(
            f"/v1/products/{inactive_product}/reactions",
            json={"reaction_type": "heart"},
        )
        assert resp.status_code == 404

    async def test_invalid_type_422(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "angry"},
        )
        assert resp.status_code == 422

    async def test_rate_limit_429(self, client, active_product):
        """10 rapid toggles exhaust the rate limit."""
        for _ in range(5):
            await client.post(
                f"/v1/products/{active_product}/reactions",
                json={"reaction_type": "heart"},
            )
            await client.post(
                f"/v1/products/{active_product}/reactions",
                json={"reaction_type": "heart"},
            )
        # 11th should be blocked
        resp = await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        assert resp.status_code == 429


class TestGetReactionsRoute:
    """GET /v1/products/{product_id}/reactions"""

    async def test_empty_counts(self, client, active_product):
        resp = await client.get(f"/v1/products/{active_product}/reactions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["heart"]["count"] == 0
        assert data["heart"]["reacted"] is False
        assert data["thumbs_up"]["count"] == 0

    async def test_counts_after_toggle(self, client, active_product):
        await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        resp = await client.get(f"/v1/products/{active_product}/reactions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["heart"]["count"] == 1
        assert data["heart"]["reacted"] is True

    async def test_inactive_product_404(self, client, inactive_product):
        resp = await client.get(f"/v1/products/{inactive_product}/reactions")
        assert resp.status_code == 404
