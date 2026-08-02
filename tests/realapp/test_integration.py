"""Integration tests — end-to-end flows combining session + cart."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.database import get_db
from app.middleware.session import rotate_session
from conftest import add_cart_item, make_session, seed_products

_INTEGRATION_PRODUCTS = (
    ("lavender-dream", "Lavender Dream", 2500, 10, True),
    ("rose-garden", "Rose Garden", 1800, 5, True),
    ("ocean-breeze", "Ocean Breeze", 1500, 20, True),
)


@pytest.fixture()
def _seed_products(app):
    """Seed products for integration tests."""
    with get_db() as conn:
        seed_products(conn, _INTEGRATION_PRODUCTS)


# --- 10.1 End-to-end: create session → add → view → update → remove ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_e2e_cart_lifecycle(client: AsyncClient):
    """Full lifecycle: create session → add item → view → update → remove."""
    # Add item (creates session implicitly)
    resp = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    assert resp.status_code == 201
    body = resp.json()
    assert body["items"][0]["quantity"] == 2
    assert body["total_cents"] == 5000

    # View cart
    resp = await client.get("/v1/cart")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["product_id"] == "lavender-dream"

    # Update quantity
    resp = await client.patch("/v1/cart/lavender-dream", json={"quantity": 4})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity"] == 4
    assert resp.json()["total_cents"] == 10000

    # Remove
    resp = await client.delete("/v1/cart/lavender-dream")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total_cents"] == 0


# --- 10.2 Session expiry + cart: expired session gets new session, old items orphaned ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_expired_session_orphans_cart(client: AsyncClient):
    """Expired session → new session, old cart items orphaned (not deleted by middleware)."""
    settings = get_settings()

    # Create session and add items
    resp = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    assert resp.status_code == 201
    old_session = resp.cookies.get(settings.session_cookie_name)

    # Expire the session directly in DB
    with get_db() as conn:
        expired_at = datetime.now(UTC) - timedelta(seconds=10)
        conn.execute(
            "UPDATE sessions SET expires_at = %s WHERE id = %s", (expired_at, old_session)
        )

    # Next request should get a new session
    client.cookies.set(settings.session_cookie_name, old_session)
    resp = await client.get("/v1/cart")
    assert resp.status_code == 200
    new_session = resp.cookies.get(settings.session_cookie_name)

    # (a) New session's cart is empty
    assert resp.json()["items"] == []
    assert new_session != old_session

    # (b) Old session row still exists with expires_at < now
    with get_db() as conn:
        row = conn.execute(
            "SELECT expires_at FROM sessions WHERE id = %s", (old_session,)
        ).fetchone()
        assert row is not None  # NOT deleted by middleware

        # (c) Old cart_items rows still present
        items = conn.execute(
            "SELECT * FROM cart_items WHERE session_id = %s", (old_session,)
        ).fetchall()
        assert len(items) == 1  # The lavender-dream item


# --- 10.3 Session rotation: add items → rotate → cart still visible ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_session_rotation_preserves_cart(client: AsyncClient):
    """Add items → rotate session → cart items still visible under new session."""
    settings = get_settings()

    # Add items
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    await client.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 1})

    # Get current session ID
    resp = await client.get("/v1/cart")
    old_session = resp.cookies.get(settings.session_cookie_name)

    # Rotate session (need a user in DB for the FK)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, google_id, email, name) VALUES (%s, %s, %s, %s)",
            ("user-xyz", "google-xyz", "user@example.com", "Test User"),
        )
        new_session = rotate_session(conn, old_session, "user-xyz")

    # Use new session and verify cart
    client.cookies.set(settings.session_cookie_name, new_session)
    resp = await client.get("/v1/cart")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    product_ids = {item["product_id"] for item in body["items"]}
    assert product_ids == {"lavender-dream", "rose-garden"}


# --- 10.4 ON DELETE CASCADE: delete session → cart_items deleted ---


@pytest.mark.usefixtures("_seed_products")
def test_cascade_delete_session_removes_cart_items(app):
    """Deleting a session row cascades to cart_items."""
    with get_db() as conn:
        # Create session + cart items
        session_id = "cascade-test-session"
        make_session(conn, session_id)
        add_cart_item(conn, session_id, "lavender-dream", 3)
        add_cart_item(conn, session_id, "rose-garden", 1)

        # Verify items exist
        items = conn.execute(
            "SELECT * FROM cart_items WHERE session_id = %s", (session_id,)
        ).fetchall()
        assert len(items) == 2

        # Delete session
        conn.execute("DELETE FROM sessions WHERE id = %s", (session_id,))

        # Verify cart items are gone (CASCADE)
        items = conn.execute(
            "SELECT * FROM cart_items WHERE session_id = %s", (session_id,)
        ).fetchall()
        assert len(items) == 0
