"""Integration tests for public product endpoints."""

import pytest


@pytest.fixture()
def _products(app, db_path):
    """Seed test products via the service layer."""
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
            "id": "midnight-amber-300ml",
            "name_en": "Midnight Amber",
            "description_en": "Warm amber and sandalwood",
            "price_cents": 4500,
            "category": "luxury-jar",
            "stock": 12,
        }
    )
    product_service.create_product(
        {
            "id": "vanilla-brulee-200ml",
            "name_en": "Vanilla Crème Brûlée",
            "description_en": "Rich vanilla custard dessert candle",
            "price_cents": 2800,
            "category": "dessert",
            "stock": 0,
        }
    )


class TestListProducts:
    """Tests for GET /v1/products."""

    @pytest.mark.asyncio
    async def test_returns_200_with_products(self, client, _products):
        response = await client.get("/v1/products")
        assert response.status_code == 200
        body = response.json()
        assert "products" in body
        assert "total" in body
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["limit"] == 20

    @pytest.mark.asyncio
    async def test_no_auth_required(self, client, _products):
        """Public endpoints work without any authentication."""
        response = await client.get("/v1/products")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_category(self, client, _products):
        response = await client.get("/v1/products?category=dessert")
        body = response.json()
        assert body["total"] == 1
        assert body["products"][0]["category"] == "dessert"

    @pytest.mark.asyncio
    async def test_filter_in_stock(self, client, _products):
        response = await client.get("/v1/products?in_stock=true")
        body = response.json()
        assert body["total"] == 2
        assert all(p["stock"] > 0 for p in body["products"])

    @pytest.mark.asyncio
    async def test_sort_by_price_asc(self, client, _products):
        response = await client.get("/v1/products?sort=price_asc")
        body = response.json()
        prices = [p["price_cents"] for p in body["products"]]
        assert prices == sorted(prices)

    @pytest.mark.asyncio
    async def test_search_by_query(self, client, _products):
        response = await client.get("/v1/products?q=lavender")
        body = response.json()
        assert body["total"] >= 1
        assert any(p["id"] == "lavender-dream-300ml" for p in body["products"])

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, client, _products):
        """Search results can be further filtered by category."""
        response = await client.get("/v1/products?q=candle&category=luxury-jar")
        body = response.json()
        assert all(p["category"] == "luxury-jar" for p in body["products"])

    @pytest.mark.asyncio
    async def test_search_with_in_stock_filter(self, client, _products):
        """Search results can be filtered to in-stock only."""
        response = await client.get("/v1/products?q=candle&in_stock=true")
        body = response.json()
        assert all(p["stock"] > 0 for p in body["products"])

    @pytest.mark.asyncio
    async def test_search_with_sort_price_asc(self, client, _products):
        """Search results can be sorted by price ascending."""
        response = await client.get("/v1/products?q=candle&sort=price_asc")
        body = response.json()
        prices = [p["price_cents"] for p in body["products"]]
        assert prices == sorted(prices)

    @pytest.mark.asyncio
    async def test_search_with_sort_price_desc(self, client, _products):
        """Search results can be sorted by price descending."""
        response = await client.get("/v1/products?q=candle&sort=price_desc")
        body = response.json()
        prices = [p["price_cents"] for p in body["products"]]
        assert prices == sorted(prices, reverse=True)

    @pytest.mark.asyncio
    async def test_search_with_sort_name(self, client, _products):
        """Search results can be sorted alphabetically by name."""
        response = await client.get("/v1/products?q=candle&sort=name")
        body = response.json()
        names = [p["name"] for p in body["products"]]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_search_with_sort_newest(self, client, _products):
        """Search results can be sorted by newest first."""
        response = await client.get("/v1/products?q=candle&sort=newest")
        body = response.json()
        # Just verify it returns 200 and has results (created_at ordering)
        assert response.status_code == 200
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_pagination(self, client, _products):
        response = await client.get("/v1/products?page=1&limit=2")
        body = response.json()
        assert body["total"] == 3
        assert len(body["products"]) == 2
        assert body["page"] == 1
        assert body["limit"] == 2

    @pytest.mark.asyncio
    async def test_empty_page(self, client, _products):
        response = await client.get("/v1/products?page=999")
        body = response.json()
        assert body["total"] == 3
        assert len(body["products"]) == 0

    @pytest.mark.asyncio
    async def test_limit_capped_at_100(self, client, _products):
        response = await client.get("/v1/products?limit=100")
        body = response.json()
        assert body["limit"] == 100

    @pytest.mark.asyncio
    async def test_limit_over_100_rejected(self, client, _products):
        response = await client.get("/v1/products?limit=500")
        assert response.status_code == 422  # FastAPI validation


class TestGetProduct:
    """Tests for GET /v1/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_returns_existing_product(self, client, _products):
        response = await client.get("/v1/products/lavender-dream-300ml")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "lavender-dream-300ml"
        assert body["name"] == "Lavender Dream"
        assert body["price_cents"] == 3200

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, client, _products):
        response = await client.get("/v1/products/no-such-product")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_returns_404_for_inactive(self, client, _products):
        from app.services import product_service

        product_service.deactivate_product("lavender-dream-300ml")
        response = await client.get("/v1/products/lavender-dream-300ml")
        assert response.status_code == 404
