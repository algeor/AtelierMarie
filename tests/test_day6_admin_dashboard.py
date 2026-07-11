"""Tests for admin dashboard endpoint and error handlers."""

import sqlite3

import pytest


@pytest.fixture()
def _seeded_data(db_path, app):
    """Seed products and orders for dashboard tests."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")

    # Products
    conn.executemany(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active) VALUES (?, ?, ?, ?, ?)",
        [
            ("candle-a", "Candle A", 2500, 20, 1),
            ("candle-b", "Candle B", 3500, 3, 1),  # low stock
            ("candle-c", "Candle C", 1500, 0, 1),  # out of stock (low stock)
            ("candle-d", "Candle D", 4000, 50, 0),  # inactive
        ],
    )

    # Session for orders
    conn.execute("INSERT INTO sessions (id, expires_at) VALUES ('sess-1', '2099-01-01 00:00:00')")

    # Orders
    conn.executemany(
        "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
        "VALUES (?, 'sess-1', ?, ?, ?)",
        [
            ("order-1", "pending", 5000, "a@test.com"),
            ("order-2", "confirmed", 7000, "b@test.com"),
            ("order-3", "shipped", 3500, "c@test.com"),
            ("order-4", "delivered", 2500, "d@test.com"),
            ("order-5", "cancelled", 4000, "e@test.com"),
        ],
    )

    conn.commit()
    conn.close()


class TestAdminDashboard:
    """Tests for GET /v1/admin/dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_empty_db(self, admin_client):
        """Dashboard works on a fresh database with no data."""
        response = await admin_client.get("/v1/admin/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert body["products"]["total"] == 0
        assert body["products"]["active"] == 0
        assert body["orders"]["total"] == 0
        assert body["orders"]["revenue_cents"] == 0
        assert body["orders"]["by_status"] == {}
        assert body["low_stock_count"] == 0

    @pytest.mark.asyncio
    async def test_dashboard_with_data(self, admin_client, _seeded_data):
        """Dashboard reports correct counts and revenue."""
        response = await admin_client.get("/v1/admin/dashboard")
        assert response.status_code == 200
        body = response.json()

        # Product stats
        assert body["products"]["total"] == 4
        assert body["products"]["active"] == 3

        # Order stats
        assert body["orders"]["total"] == 5
        assert body["orders"]["revenue_cents"] == 22000  # sum of all orders
        assert body["orders"]["by_status"]["pending"] == 1
        assert body["orders"]["by_status"]["confirmed"] == 1
        assert body["orders"]["by_status"]["shipped"] == 1
        assert body["orders"]["by_status"]["delivered"] == 1
        assert body["orders"]["by_status"]["cancelled"] == 1

        # Low stock (stock <= 5 AND active): candle-b (3), candle-c (0)
        assert body["low_stock_count"] == 2

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, app):
        """Dashboard endpoint requires admin credentials."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/v1/admin/dashboard")
            assert response.status_code == 401


class TestErrorHandlers:
    """Tests for global exception handlers."""

    @pytest.mark.asyncio
    async def test_validation_error_format(self, admin_client):
        """Validation errors return consistent envelope."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={"id": "x", "name_en": "", "price_cents": -1, "stock": 0},
        )
        assert response.status_code == 422
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "message" in body["error"]
        assert "details" in body["error"]
        assert "errors" in body["error"]["details"]

    @pytest.mark.asyncio
    async def test_404_error_format(self, admin_client):
        """404 errors follow consistent format."""
        response = await admin_client.get("/v1/admin/products/no-such-product")
        assert response.status_code == 404
        body = response.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_401_error_format(self, app):
        """401 errors follow consistent format."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401
            body = response.json()
            assert "error" in body
            assert body["error"]["code"] == "UNAUTHORIZED"


class TestInputValidationEdgeCases:
    """Tests for input validation hardening."""

    @pytest.mark.asyncio
    async def test_whitespace_only_name_rejected(self, admin_client):
        """Whitespace-only name is rejected."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={"id": "test-candle", "name_en": "   ", "price_cents": 1000, "stock": 5},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_name_stripped(self, admin_client):
        """Leading/trailing whitespace in name is trimmed."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "trim-test",
                "name_en": "  Trimmed Name  ",
                "price_cents": 1000,
                "stock": 5,
            },
        )
        assert response.status_code == 201
        assert response.json()["name_en"] == "Trimmed Name"

    @pytest.mark.asyncio
    async def test_negative_price_rejected(self, admin_client):
        """Negative price is rejected."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={"id": "negative-price", "name_en": "Bad", "price_cents": -100, "stock": 5},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_zero_price_rejected(self, admin_client):
        """Zero price is rejected (price must be gt=0)."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={"id": "zero-price", "name_en": "Free", "price_cents": 0, "stock": 5},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_huge_price_rejected(self, admin_client):
        """Price exceeding max (99_999_99) is rejected."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "huge-price",
                "name_en": "Expensive",
                "price_cents": 100_000_00,
                "stock": 5,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_huge_stock_rejected(self, admin_client):
        """Stock exceeding max (99999) is rejected."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={"id": "huge-stock", "name_en": "Many", "price_cents": 1000, "stock": 100000},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_stock_rejected(self, admin_client):
        """Negative stock is rejected."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={"id": "neg-stock", "name_en": "Negative", "price_cents": 1000, "stock": -1},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_image_url_rejected(self, admin_client):
        """Image URL that doesn't start with http(s):// or / is rejected."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "bad-url",
                "name_en": "Bad URL",
                "price_cents": 1000,
                "stock": 5,
                "image_url": "ftp://evil.com/image.jpg",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_relative_image_url_accepted(self, admin_client):
        """Relative URL (starts with /) is accepted."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "relative-url",
                "name_en": "Relative URL Product",
                "price_cents": 1000,
                "stock": 5,
                "image_url": "/static/products/relative-url.webp",
            },
        )
        assert response.status_code == 201
        assert response.json()["image_url"] == "/static/products/relative-url.webp"

    @pytest.mark.asyncio
    async def test_valid_https_image_url_accepted(self, admin_client):
        """HTTPS URL is accepted."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "https-url",
                "name_en": "HTTPS URL Product",
                "price_cents": 1000,
                "stock": 5,
                "image_url": "https://cdn.example.com/image.webp",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_invalid_product_id_pattern(self, admin_client):
        """Product IDs must match slug pattern."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "Invalid ID With Spaces!",
                "name_en": "Bad ID",
                "price_cents": 1000,
                "stock": 5,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_days_to_craft_max(self, admin_client):
        """days_to_craft is capped at 365."""
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "slow-candle",
                "name_en": "Very Slow Candle",
                "price_cents": 1000,
                "stock": 5,
                "days_to_craft": 400,
            },
        )
        assert response.status_code == 422
