"""Tests for cart route layer — HTTP status codes, error formats, validation."""

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import init_db

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def _seed_products(db_path: str, app):
    """Seed products for cart route tests."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    products = [
        ("lavender-dream", "Lavender Dream", 2500, 10, 1),
        ("rose-garden", "Rose Garden", 1800, 5, 1),
        ("midnight-musk", "Midnight Musk", 3200, 0, 1),  # Out of stock
        ("winter-pine", "Winter Pine", 2000, 8, 0),  # Inactive
        ("ocean-breeze", "Ocean Breeze", 1500, 20, 1),
    ]
    for pid, name, price, stock, active in products:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, "
            "is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (pid, name, price, stock, active),
        )
    conn.commit()
    conn.close()


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
async def test_get_cart_unavailable_items(client: AsyncClient, db_path: str):
    """GET /v1/cart — 200 with unavailable_items populated."""
    # Add item then deactivate it
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 1})

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE products SET is_active = 0 WHERE id = 'lavender-dream'")
    conn.commit()
    conn.close()

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
async def test_post_cart_insufficient_stock_409(client: AsyncClient):
    """POST /v1/cart — 409 for insufficient stock with correct error structure."""
    response = await client.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 6})
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INSUFFICIENT_STOCK"
    assert body["error"]["details"]["product_id"] == "rose-garden"
    assert body["error"]["details"]["requested"] == 6
    assert body["error"]["details"]["available"] == 5


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
async def test_post_cart_cart_full_422(client: AsyncClient, db_path: str):
    """POST /v1/cart — 422 for cart full."""
    # Create 20 products and fill cart
    conn = sqlite3.connect(db_path)
    for i in range(20):
        pid = f"fill-route-{i:03d}"
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, "
            "is_active, created_at, updated_at) "
            "VALUES (?, ?, 1000, 50, 1, datetime('now'), datetime('now'))",
            (pid, f"Fill Route {i}"),
        )
    conn.commit()
    conn.close()

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
async def test_patch_cart_insufficient_stock_409(client: AsyncClient):
    """PATCH /v1/cart/{product_id} — 409 for stock exceeded."""
    await client.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 2})
    response = await client.patch("/v1/cart/rose-garden", json={"quantity": 8})
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INSUFFICIENT_STOCK"
    assert body["error"]["details"]["available"] == 5


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_patch_cart_limit_422(client: AsyncClient):
    """PATCH /v1/cart/{product_id} — 422 for limit exceeded."""
    await client.post("/v1/cart", json={"product_id": "ocean-breeze", "quantity": 5})
    response = await client.patch("/v1/cart/ocean-breeze", json={"quantity": 15})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "QUANTITY_LIMIT_EXCEEDED"


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
    """POST /v1/cart with quantity=100 → 422 (Pydantic le=99)."""
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
async def test_cart_isolation_between_sessions(tmp_path, monkeypatch):
    """Different sessions have independent carts (requires real session middleware)."""
    # This test needs real middleware — create a standalone app inline.
    db_file = str(tmp_path / "isolation.db")
    monkeypatch.setenv("DATABASE_PATH", db_file)
    monkeypatch.setenv("ADMIN_API_KEY", "test-key")
    get_settings.cache_clear()
    init_db(db_file)

    # Seed products
    conn = sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at) "
        "VALUES ('lavender-dream', 'Lavender Dream', 2500, 10, 1, datetime('now'), datetime('now'))"
    )
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at) "
        "VALUES ('rose-garden', 'Rose Garden', 1800, 5, 1, datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

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

    get_settings.cache_clear()
