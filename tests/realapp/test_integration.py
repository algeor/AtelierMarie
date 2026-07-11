"""Integration tests — end-to-end flows combining session + cart."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.middleware.session import rotate_session

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def _seed_products(db_path: str, app):
    """Seed products for integration tests."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    products = [
        ("lavender-dream", "Lavender Dream", 2500, 10, 1),
        ("rose-garden", "Rose Garden", 1800, 5, 1),
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
async def test_expired_session_orphans_cart(client: AsyncClient, db_path: str):
    """Expired session → new session, old cart items orphaned (not deleted by middleware)."""
    settings = get_settings()

    # Create session and add items
    resp = await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    assert resp.status_code == 201
    old_session = resp.cookies.get(settings.session_cookie_name)

    # Expire the session directly in DB
    conn = sqlite3.connect(db_path)
    expired_at = (datetime.now(UTC) - timedelta(seconds=10)).strftime(_DT_FMT)
    conn.execute("UPDATE sessions SET expires_at = ? WHERE id = ?", (expired_at, old_session))
    conn.commit()
    conn.close()

    # Next request should get a new session
    client.cookies.set(settings.session_cookie_name, old_session)
    resp = await client.get("/v1/cart")
    assert resp.status_code == 200
    new_session = resp.cookies.get(settings.session_cookie_name)

    # (a) New session's cart is empty
    assert resp.json()["items"] == []
    assert new_session != old_session

    # (b) Old session row still exists with expires_at < now
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT expires_at FROM sessions WHERE id = ?", (old_session,)).fetchone()
    assert row is not None  # NOT deleted by middleware

    # (c) Old cart_items rows still present
    items = conn.execute("SELECT * FROM cart_items WHERE session_id = ?", (old_session,)).fetchall()
    assert len(items) == 1  # The lavender-dream item
    conn.close()


# --- 10.3 Session rotation: add items → rotate → cart still visible ---


@pytest.mark.asyncio
@pytest.mark.usefixtures("_seed_products")
async def test_session_rotation_preserves_cart(client: AsyncClient, db_path: str):
    """Add items → rotate session → cart items still visible under new session."""
    settings = get_settings()

    # Add items
    await client.post("/v1/cart", json={"product_id": "lavender-dream", "quantity": 2})
    await client.post("/v1/cart", json={"product_id": "rose-garden", "quantity": 1})

    # Get current session ID
    resp = await client.get("/v1/cart")
    old_session = resp.cookies.get(settings.session_cookie_name)

    # Rotate session (need a user in DB for the FK)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO users (id, google_id, email, name) VALUES (?, ?, ?, ?)",
        ("user-xyz", "google-xyz", "user@example.com", "Test User"),
    )
    conn.commit()
    new_session = rotate_session(conn, old_session, "user-xyz")
    conn.close()

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
def test_cascade_delete_session_removes_cart_items(db_path: str, app):
    """Deleting a session row cascades to cart_items."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    now = datetime.now(UTC)

    # Create session + cart items
    session_id = "cascade-test-session"
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_id, "lavender-dream", 3),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_id, "rose-garden", 1),
    )
    conn.commit()

    # Verify items exist
    items = conn.execute("SELECT * FROM cart_items WHERE session_id = ?", (session_id,)).fetchall()
    assert len(items) == 2

    # Delete session
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()

    # Verify cart items are gone (CASCADE)
    items = conn.execute("SELECT * FROM cart_items WHERE session_id = ?", (session_id,)).fetchall()
    assert len(items) == 0
    conn.close()
