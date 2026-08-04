"""Integration tests for public product endpoints."""

import sqlite3

import pytest

from app.config import get_settings
from app.models.users import UserResponse
from app.services import auth_service


def _authenticate_client(client, db_path: str, app) -> None:
    """Attach a valid JWT for the fake middleware session used by route tests."""
    user = UserResponse(
        id="saved-user",
        email="saved@example.com",
        name="Saved User",
        avatar_url=None,
        is_admin=False,
    )
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, google_id, email, name) VALUES (?, ?, ?, ?)",
        (user.id, "google-saved", user.email, user.name),
    )
    conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user.id, app._test_session_id))
    conn.commit()
    conn.close()

    client.cookies.clear()
    client.cookies.set(
        get_settings().jwt_cookie_name,
        auth_service.create_jwt(user, app._test_session_id),
    )


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
            "category": "medium",
            "stock": 24,
        }
    )
    product_service.create_product(
        {
            "id": "midnight-amber-300ml",
            "name_en": "Midnight Amber",
            "description_en": "Warm amber and sandalwood",
            "price_cents": 4500,
            "category": "medium",
            "stock": 12,
        }
    )
    product_service.create_product(
        {
            "id": "vanilla-brulee-200ml",
            "name_en": "Vanilla Crème Brûlée",
            "description_en": "Rich vanilla custard dessert candle",
            "price_cents": 2800,
            "category": "small",
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
        response = await client.get("/v1/products?category=small")
        body = response.json()
        assert body["total"] == 1
        assert body["products"][0]["category"] == "small"

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
        response = await client.get("/v1/products?q=candle&category=medium")
        body = response.json()
        assert all(p["category"] == "medium" for p in body["products"])

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
    async def test_public_response_omits_weight(self, client, _products):
        """weight_grams is a shipping input, not a customer-facing attribute."""
        response = await client.get("/v1/products/lavender-dream-300ml")
        assert response.status_code == 200
        assert "weight_grams" not in response.json()

    @pytest.mark.asyncio
    async def test_public_response_includes_safety_metadata_with_locale_fallback(self, client):
        from app.services import product_service

        product_service.create_product(
            {
                "id": "route-safety-candle",
                "name_en": "Safety Candle",
                "name_bg": "Безопасна свещ",
                "price_cents": 2400,
                "stock": 6,
                "safety_warnings_en": "Keep away from curtains.",
                "safety_warnings_bg": "Дръжте далеч от завеси.",
                "care_instructions_en": "Trim wick before each burn.",
            }
        )

        detail = await client.get("/v1/products/route-safety-candle?locale=bg")
        assert detail.status_code == 200
        body = detail.json()
        assert body["safety_warnings"] == "Дръжте далеч от завеси."
        assert body["care_instructions"] == "Trim wick before each burn."
        assert "safety_warnings_en" not in body

        listing = await client.get("/v1/products?locale=bg")
        products = listing.json()["products"]
        listed = next(p for p in products if p["id"] == "route-safety-candle")
        assert listed["safety_warnings"] == "Дръжте далеч от завеси."
        assert listed["care_instructions"] == "Trim wick before each burn."

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, client, _products):
        response = await client.get("/v1/products/no-such-product")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["details"] is None

    @pytest.mark.asyncio
    async def test_returns_404_for_inactive(self, client, _products):
        from app.services import product_service

        product_service.deactivate_product("lavender-dream-300ml")
        response = await client.get("/v1/products/lavender-dream-300ml")
        assert response.status_code == 404


class TestSavedProducts:
    """Tests for authenticated saved-product endpoints."""

    @pytest.mark.asyncio
    async def test_saved_products_require_auth(self, client, _products):
        client.cookies.clear()
        response = await client.get("/v1/products/saved")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_save_list_and_unsave_product(self, client, db_path, app, _products):
        _authenticate_client(client, db_path, app)

        save_response = await client.post("/v1/products/lavender-dream-300ml/saved")
        assert save_response.status_code == 201
        assert save_response.json() == {
            "product_id": "lavender-dream-300ml",
            "saved": True,
        }

        list_response = await client.get("/v1/products/saved")
        assert list_response.status_code == 200
        body = list_response.json()
        assert body["total"] == 1
        assert body["product_ids"] == ["lavender-dream-300ml"]
        assert body["products"][0]["id"] == "lavender-dream-300ml"

        delete_response = await client.delete("/v1/products/lavender-dream-300ml/saved")
        assert delete_response.status_code == 200
        assert delete_response.json() == {
            "product_id": "lavender-dream-300ml",
            "saved": False,
        }

        empty_response = await client.get("/v1/products/saved")
        assert empty_response.status_code == 200
        assert empty_response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_save_missing_product_returns_404(self, client, db_path, app, _products):
        _authenticate_client(client, db_path, app)

        response = await client.post("/v1/products/missing/saved")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
