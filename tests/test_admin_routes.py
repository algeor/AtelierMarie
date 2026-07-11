"""Integration tests for admin product endpoints."""

import pytest


@pytest.fixture()
def _products(db_path, app):
    """Seed test products."""
    from app.services import product_service

    product_service.create_product(
        {
            "id": "lavender-dream-300ml",
            "name_en": "Lavender Dream",
            "description_en": "A calming lavender candle",
            "price_cents": 3200,
            "category": "luxury-jar",
            "stock": 24,
        }
    )
    product_service.create_product(
        {
            "id": "inactive-candle",
            "name_en": "Inactive Candle",
            "description_en": "This one is deactivated",
            "price_cents": 1000,
            "category": "seasonal",
            "stock": 5,
            "is_active": False,
        }
    )


class TestAdminAuth:
    """Tests for admin authentication dependency."""

    @pytest.mark.asyncio
    async def test_rejects_no_credentials(self, app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_invalid_key(self, app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer wrong-key"
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_empty_key(self, app, monkeypatch):
        """Empty API key config denies all access."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "admin_api_key", "")

        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer "
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_valid_key(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products")
        assert response.status_code == 200


class TestAdminCreateProduct:
    """Tests for POST /v1/admin/products."""

    @pytest.mark.asyncio
    async def test_creates_product(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "new-candle-100ml",
                "name_en": "New Candle",
                "price_cents": 2000,
                "stock": 10,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["id"] == "new-candle-100ml"
        assert body["name_en"] == "New Candle"
        assert body["price_cents"] == 2000

    @pytest.mark.asyncio
    async def test_returns_409_for_duplicate(self, admin_client, _products):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "lavender-dream-300ml",
                "name_en": "Duplicate",
                "price_cents": 1000,
                "stock": 1,
            },
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "DUPLICATE"

    @pytest.mark.asyncio
    async def test_returns_422_for_invalid_data(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "x",
                "name_en": "",
                "price_cents": -1,
                "stock": 0,
            },
        )
        assert response.status_code == 422


class TestAdminListProducts:
    """Tests for GET /v1/admin/products."""

    @pytest.mark.asyncio
    async def test_lists_all_products_including_inactive(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        ids = [p["id"] for p in body["products"]]
        assert "inactive-candle" in ids

    @pytest.mark.asyncio
    async def test_pagination(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products?page=1&limit=1")
        body = response.json()
        assert body["total"] == 2
        assert len(body["products"]) == 1


class TestAdminGetProduct:
    """Tests for GET /v1/admin/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_returns_active_product(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/lavender-dream-300ml")
        assert response.status_code == 200
        assert response.json()["name_en"] == "Lavender Dream"

    @pytest.mark.asyncio
    async def test_returns_inactive_product(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/inactive-candle")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/no-such-product")
        assert response.status_code == 404


class TestAdminUpdateProduct:
    """Tests for PUT /v1/admin/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_partial_update(self, admin_client, _products):
        response = await admin_client.put(
            "/v1/admin/products/lavender-dream-300ml",
            json={"name_en": "Lavender Dream XL"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name_en"] == "Lavender Dream XL"
        assert body["price_cents"] == 3200  # Unchanged

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, admin_client, _products):
        response = await admin_client.put(
            "/v1/admin/products/no-such-product",
            json={"name_en": "X"},
        )
        assert response.status_code == 404


class TestAdminDeleteProduct:
    """Tests for DELETE /v1/admin/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_soft_deletes_product(self, admin_client, _products):
        response = await admin_client.delete("/v1/admin/products/lavender-dream-300ml")
        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, admin_client, _products):
        response = await admin_client.delete("/v1/admin/products/no-such-product")
        assert response.status_code == 404


class TestAdminCSVImport:
    """Tests for POST /v1/admin/products/import."""

    @pytest.mark.asyncio
    async def test_imports_new_products(self, admin_client):
        csv_content = (
            "id,name,price_cents,stock,category\n"
            "csv-candle-1,CSV Candle One,2000,10,dessert\n"
            "csv-candle-2,CSV Candle Two,3000,5,luxury-jar\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["created"] == 2
        assert body["updated"] == 0
        assert body["errors"] == []

    @pytest.mark.asyncio
    async def test_upsert_existing_products(self, admin_client, _products):
        csv_content = (
            "id,name,price_cents,stock\n"
            "lavender-dream-300ml,Updated Lavender,3500,30\n"
            "new-product-csv,Brand New,1500,20\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1
        assert body["updated"] == 1
        assert body["errors"] == []

    @pytest.mark.asyncio
    async def test_validation_errors_skip_rows(self, admin_client):
        csv_content = (
            "id,name,price_cents,stock\n"
            "good-candle,Good Candle,2000,10\n"
            ",Missing ID,2000,10\n"
            "bad-price,Bad Price,-100,10\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1
        assert len(body["errors"]) == 2
        # Check row numbers
        error_rows = [e["row"] for e in body["errors"]]
        assert 3 in error_rows
        assert 4 in error_rows

    @pytest.mark.asyncio
    async def test_missing_required_columns(self, admin_client):
        csv_content = "name,stock\nSome Product,10\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "INVALID_CSV"
        assert "id" in body["error"]["message"]
        assert "price_cents" in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_empty_csv_headers_only(self, admin_client):
        csv_content = "id,name,price_cents\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["created"] == 0
        assert body["updated"] == 0
        assert body["errors"] == []
