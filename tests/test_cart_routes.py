"""Tests for cart route layer — HTTP status codes, error formats, validation."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_db
from conftest import seed_products


@pytest.fixture()
def _seed_products(app):
    """Seed products for cart route tests (shared default catalog)."""
    with get_db() as conn:
        seed_products(conn)


# --- 9.1 Test GET /v1/cart ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_get_cart_empty(client: AsyncClient):
    """GET /v1/cart — 200 with empty cart."""
    response = await client.get("/v1/cart")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total_cents"] == 0
    assert body["item_count"] == 0
    assert body["unavailable_items"] == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_get_cart_with_items(client: AsyncClient):
    """GET /v1/cart — 200 with items."""
    # Add an item first
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})

    response = await client.get("/v1/cart")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == "lavender-dream"
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["product"]["name"] == "Lavender Dream"
    assert body["total_cents"] == 5000  # 2500 × 2


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_get_cart_unavailable_items(client: AsyncClient):
    """GET /v1/cart — 200 with unavailable_items populated."""
    # Add item then deactivate it
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 1})

    with get_db() as conn:
        conn.execute("UPDATE products SET is_active = 0 WHERE id = 'lavender-dream'")

    response = await client.get("/v1/cart")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 0
    assert len(body["unavailable_items"]) == 1
    assert body["unavailable_items"][0]["product_id"] == "lavender-dream"
    assert body["unavailable_items"][0]["product_name"] == "Lavender Dream"
    assert body["unavailable_items"][0]["reason"] == "deactivated"


# --- 9.2 Test POST /v1/cart ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_new_item_201(client: AsyncClient):
    """POST /v1/cart — 201 for new item."""
    response = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 1})
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_existing_item_200(client: AsyncClient):
    """POST /v1/cart — 200 for existing item (increment)."""
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 1})
    response = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["quantity"] == 3


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_product_not_found_404(client: AsyncClient):
    """POST /v1/cart — 404 for non-existent product."""
    response = await client.post(
        "/v1/cart", json={"product_id": "nonexistent-product", "quantity": 1}
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_allows_out_of_stock_active_product(client: AsyncClient):
    """POST /v1/cart accepts active products even when requested quantity exceeds stock."""
    response = await client.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 6})
    assert response.status_code == 201
    body = response.json()
    assert body["items"][0]["product_id"] == "rose-garden"
    assert body["items"][0]["quantity"] == 6
    assert body["items"][0]["product"]["can_order"] is True


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_quantity_limit_422(client: AsyncClient):
    """POST /v1/cart — 422 for quantity limit exceeded."""
    # Add 8, then try to add 4 more (total 12 > max 10)
    await client.post("/v1/cart", json={"product_id": "ocean-breeze", "quantity": 8})
    response = await client.post("/v1/cart", json={"product_id": "ocean-breeze", "quantity": 4})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "QUANTITY_LIMIT_EXCEEDED"
    assert body["error"]["details"]["max_quantity"] == 10


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_cart_full_422(client: AsyncClient):
    """POST /v1/cart — 422 for cart full."""
    # Create 20 products and fill cart
    with get_db() as conn:
        for i in range(20):
            pid = f"fill-route-{i:03d}"
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, "
                "is_active, created_at, updated_at) "
                "VALUES (%s, %s, 1000, 50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (pid, f"Fill Route {i}"),
            )

    for i in range(20):
        resp = await client.post(
            "/v1/cart", json={"product_id": f"fill-route-{i:03d}", "quantity": 1}
        )
        assert resp.status_code == 201

    # 21st should fail
    response = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 1})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "CART_FULL"
    assert body["error"]["details"]["max_items"] == 20


# --- 9.3 Test PATCH /v1/cart/{product_id} ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_update_200(client: AsyncClient):
    """PATCH /v1/cart/{product_id} — 200 for valid update."""
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    response = await client.patch("/v1/cart/lavender-dream", json={"quantity": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["quantity"] == 5


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_remove_qty_zero_200(client: AsyncClient):
    """PATCH /v1/cart/{product_id} — 200 for quantity=0 (remove)."""
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    response = await client.patch("/v1/cart/lavender-dream", json={"quantity": 0})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_not_in_cart_404(client: AsyncClient):
    """PATCH /v1/cart/{product_id} — 404 for item not in cart."""
    response = await client.patch("/v1/cart/lavender-dream", json={"quantity": 3})
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "CART_ITEM_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_allows_quantity_beyond_stock(client: AsyncClient):
    """PATCH /v1/cart/{product_id} uses cart limits instead of stock caps."""
    await client.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 2})
    response = await client.patch("/v1/cart/rose-garden", json={"quantity": 8})
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["product_id"] == "rose-garden"
    assert body["items"][0]["quantity"] == 8


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_limit_422(client: AsyncClient):
    """PATCH /v1/cart/{product_id} — 422 for limit exceeded.

    quantity=15 exceeds the Pydantic `le=10` bound (matching
    cart_max_quantity_per_item), so validation rejects it before the service
    ever runs — the response code is VALIDATION_ERROR, not
    QUANTITY_LIMIT_EXCEEDED. Both are 422; the meaning ("over the limit") is
    preserved.
    """
    await client.post("/v1/cart", json={"product_id": "ocean-breeze", "quantity": 5})
    response = await client.patch("/v1/cart/ocean-breeze", json={"quantity": 15})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


# --- 9.4 Test DELETE /v1/cart/{product_id} ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_delete_cart_item_200(client: AsyncClient):
    """DELETE /v1/cart/{product_id} — 200 for removed item."""
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    response = await client.delete("/v1/cart/lavender-dream")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_delete_cart_item_not_found_404(client: AsyncClient):
    """DELETE /v1/cart/{product_id} — 404 for item not in cart."""
    response = await client.delete("/v1/cart/lavender-dream")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "CART_ITEM_NOT_FOUND"


# --- 9.5 Test Pydantic validation ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_invalid_product_id_format_422(client: AsyncClient):
    """POST /v1/cart with invalid product_id format → 422."""
    response = await client.post("/v1/cart", json={"product_id": "UPPER_CASE", "quantity": 1})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_quantity_zero_422(client: AsyncClient):
    """POST /v1/cart with quantity=0 → 422 (Pydantic ge=1)."""
    response = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 0})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_quantity_100_422(client: AsyncClient):
    """POST /v1/cart with quantity=100 → 422 (Pydantic le=10)."""
    response = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 100})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_quantity_negative_422(client: AsyncClient):
    """PATCH with quantity=-1 → 422."""
    response = await client.patch("/v1/cart/lavender-dream", json={"quantity": -1})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_post_cart_missing_required_fields_422(client: AsyncClient):
    """POST with missing required fields → 422."""
    response = await client.post("/v1/cart", json={})
    assert response.status_code == 422


# --- 9.6 Test path parameter validation ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_uppercase_product_id_422(client: AsyncClient):
    """PATCH with uppercase product_id → 422."""
    response = await client.patch("/v1/cart/UPPER_CASE", json={"quantity": 1})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_delete_uppercase_product_id_422(client: AsyncClient):
    """DELETE with uppercase product_id → 422."""
    response = await client.delete("/v1/cart/UPPER_CASE")
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_oversized_product_id_422(client: AsyncClient):
    """PATCH with oversized product_id (>100 chars) → 422."""
    long_id = "a" * 101
    response = await client.patch(f"/v1/cart/{long_id}", json={"quantity": 1})
    assert response.status_code == 422


# --- 9.7 Test cart isolation between sessions ---


@pytest.mark.asyncio
async def test_cart_isolation_between_sessions(app):
    """Different sessions have independent carts (requires real session middleware).

    The shared ``app`` fixture installs ``FakeSessionMiddleware``, which pins every
    request to one session id — useless for an isolation test. We depend on ``app``
    only to guarantee the psycopg pool is open against this worker's DB, then build
    a fresh app with the REAL ``SessionMiddleware`` bound to the same pool.
    """
    # Seed products via the pooled connection (worker DB already provisioned).
    with get_db() as conn:
        seed_products(
            conn,
            (
                ("lavender-dream", "Lavender Dream", 2500, 10, True),
                ("rose-garden", "Rose Garden", 1800, 5, True),
            ),
        )

    from app.main import create_app

    real_app = create_app()
    settings = get_settings()
    transport = ASGITransport(app=real_app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Session A adds lavender-dream
        resp_a = await c.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
        assert resp_a.status_code == 201
        session_a_cookie = resp_a.cookies.get(settings.session_cookie_name)

        # Create a new session by clearing cookies
        c.cookies.clear()

        # Session B adds rose-garden
        resp_b_init = await c.get("/v1/cart")
        session_b_cookie = resp_b_init.cookies.get(settings.session_cookie_name)
        assert session_b_cookie != session_a_cookie

        resp_b = await c.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 3})
        assert resp_b.status_code == 201

        # Verify session B's cart has only rose-garden
        resp_b_cart = await c.get("/v1/cart")
        body_b = resp_b_cart.json()
        assert len(body_b["items"]) == 1
        assert body_b["items"][0]["product_id"] == "rose-garden"

        # Switch to session A and verify it has lavender-dream
        c.cookies.set(settings.session_cookie_name, session_a_cookie)
        resp_a_cart = await c.get("/v1/cart")
        body_a = resp_a_cart.json()
        assert len(body_a["items"]) == 1
        assert body_a["items"][0]["product_id"] == "lavender-dream"
