"""Integration tests for order routes with TestClient."""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture(autouse=True)
def _seed_order_products(db_path, app):
    """Seed products needed by order tests (uses realapp conftest's app)."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at) "
        "VALUES ('lavender-dream', 'Lavender Dream', 2500, 10, 1, datetime('now'), datetime('now'))"
    )
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at) "
        "VALUES ('midnight-amber', 'Midnight Amber', 3500, 5, 1, datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def order_session_id(db_path):
    """Insert a session and cart items, return session_id."""
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, 'lavender-dream', 2)",
        (sid,),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, 'midnight-amber', 1)",
        (sid,),
    )
    conn.commit()
    conn.close()
    return sid


@pytest.fixture()
async def order_client(app, order_session_id) -> AsyncClient:
    """Client with session cookie and cart items."""
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(settings.session_cookie_name, order_session_id)
        yield c


@pytest.fixture()
async def admin_order_client(app, order_session_id) -> AsyncClient:
    """Client with admin auth header and session cookie."""
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(settings.session_cookie_name, order_session_id)
        c.headers["Authorization"] = "Bearer test-admin-key-realapp"
        yield c


# ===========================================================================
# 7.2: POST /v1/orders returns 201 on success
# ===========================================================================


class TestCreateOrder:
    """Integration tests for POST /v1/orders."""

    async def test_checkout_success_201(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "marie@example.com", "customer_name": "Marie"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["customer_email"] == "marie@example.com"
        assert data["total_cents"] == 2500 * 2 + 3500 * 1
        assert len(data["items"]) == 2

    # 7.3: POST returns 400 on empty cart, 409 on stock issues
    async def test_checkout_empty_cart_400(self, app, db_path):
        """Empty cart returns 400."""
        # Create session without cart items
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, sid)
            resp = await c.post("/v1/orders", json={"customer_email": "t@t.com"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "EMPTY_CART"

    async def test_checkout_insufficient_stock_409(self, app, db_path):
        """Insufficient stock returns 409."""
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        # Request 10 but only 5 in stock
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'midnight-amber', 6)",
            (sid,),
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, sid)
            resp = await c.post("/v1/orders", json={"customer_email": "t@t.com"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # 7.4: POST returns 422 for invalid email, overly long fields
    async def test_invalid_email_422(self, order_client):
        resp = await order_client.post("/v1/orders", json={"customer_email": "not-an-email"})
        assert resp.status_code == 422

    async def test_overly_long_customer_name_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "ok@ok.com", "customer_name": "X" * 201},
        )
        assert resp.status_code == 422

    async def test_overly_long_shipping_address_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "ok@ok.com", "shipping_address": "X" * 1001},
        )
        assert resp.status_code == 422

    async def test_overly_long_notes_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "ok@ok.com", "notes": "X" * 2001},
        )
        assert resp.status_code == 422


# ===========================================================================
# 7.5: GET /v1/orders returns paginated list
# ===========================================================================


class TestListMyOrders:
    """Integration tests for GET /v1/orders."""

    async def test_list_orders_paginated(self, order_client):
        # Create an order first
        await order_client.post("/v1/orders", json={"customer_email": "t@t.com"})

        resp = await order_client.get("/v1/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["page"] == 1

    # 7.5b: Cross-session isolation
    async def test_cross_session_isolation(self, app, db_path, order_session_id):
        """Orders from session A not visible to session B."""
        settings = get_settings()

        # Create order with session A
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, order_session_id)
            resp = await c.post("/v1/orders", json={"customer_email": "a@a.com"})
            assert resp.status_code == 201

        # Create session B (no orders)
        sid_b = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid_b, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        conn.commit()
        conn.close()

        # Session B sees no orders
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, sid_b)
            resp = await c.get("/v1/orders")
            assert resp.status_code == 200
            assert resp.json()["total"] == 0


# ===========================================================================
# 7.6: GET /v1/orders/{id} returns 404 for non-owner
# ===========================================================================


class TestGetOrderDetail:
    """Integration tests for GET /v1/orders/{id}."""

    async def test_non_owner_gets_404(self, app, db_path, order_session_id):
        settings = get_settings()
        transport = ASGITransport(app=app)

        # Create order with session A
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, order_session_id)
            resp = await c.post("/v1/orders", json={"customer_email": "a@a.com"})
            order_id = resp.json()["id"]

        # Session B tries to access
        sid_b = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid_b, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        conn.commit()
        conn.close()

        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, sid_b)
            resp = await c.get(f"/v1/orders/{order_id}")
            assert resp.status_code == 404


# ===========================================================================
# 7.7: PATCH /v1/admin/orders/{id}/status returns 422 on invalid transition
# ===========================================================================


class TestAdminUpdateStatus:
    """Integration tests for PATCH /v1/admin/orders/{id}/status."""

    async def test_invalid_transition_422(self, admin_order_client):
        # Create order
        resp = await admin_order_client.post("/v1/orders", json={"customer_email": "t@t.com"})
        order_id = resp.json()["id"]

        # Try invalid transition: pending → shipped
        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"


# ===========================================================================
# 7.8: Admin routes return 401/403 for non-admin sessions
# ===========================================================================


class TestAdminAuth:
    """Non-admin cannot access admin order routes."""

    async def test_admin_list_orders_no_auth(self, order_client):
        resp = await order_client.get("/v1/admin/orders")
        assert resp.status_code == 401

    async def test_admin_get_order_no_auth(self, order_client):
        resp = await order_client.get("/v1/admin/orders/some-id")
        assert resp.status_code == 401

    async def test_admin_update_status_no_auth(self, order_client):
        resp = await order_client.patch(
            "/v1/admin/orders/some-id/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 401


# ===========================================================================
# 7.9: GET /v1/admin/orders returns all orders paginated, with status filter
# ===========================================================================


class TestAdminListOrders:
    """Integration tests for GET /v1/admin/orders."""

    async def test_admin_list_all_orders(self, admin_order_client):
        # Create an order
        await admin_order_client.post("/v1/orders", json={"customer_email": "t@t.com"})

        resp = await admin_order_client.get("/v1/admin/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_admin_filter_by_status(self, admin_order_client):
        # Create an order (status: pending)
        await admin_order_client.post("/v1/orders", json={"customer_email": "t@t.com"})

        # Filter by pending
        resp = await admin_order_client.get("/v1/admin/orders?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert all(o["status"] == "pending" for o in data["items"])

        # Filter by confirmed (should be empty)
        resp = await admin_order_client.get("/v1/admin/orders?status=confirmed")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_admin_filter_and_pagination(self, admin_order_client):
        resp = await admin_order_client.get("/v1/admin/orders?status=pending&page=1&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["limit"] == 5


# ===========================================================================
# 7.10: GET /v1/admin/orders?status=invalid returns 422
# ===========================================================================


class TestAdminInvalidStatusFilter:
    """Invalid status filter returns 422."""

    async def test_invalid_status_422(self, admin_order_client):
        resp = await admin_order_client.get("/v1/admin/orders?status=invalid")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_STATUS"


# ===========================================================================
# 7.11: GET /v1/admin/orders/{id} returns full detail for admin, 401 for non-admin
# ===========================================================================


class TestAdminGetOrderDetail:
    """Integration tests for GET /v1/admin/orders/{id}."""

    async def test_admin_gets_full_detail(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test",
                "shipping_address": "123 St",
                "notes": "Handle with care",
            },
        )
        order_id = resp.json()["id"]

        resp = await admin_order_client.get(f"/v1/admin/orders/{order_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_email"] == "t@t.com"
        assert data["customer_name"] == "Test"
        assert data["shipping_address"] == "123 St"
        assert data["notes"] == "Handle with care"
        assert len(data["items"]) == 2

    async def test_non_admin_gets_401(self, order_client):
        resp = await order_client.get("/v1/admin/orders/some-id")
        assert resp.status_code == 401


# ===========================================================================
# 7.12: POST /v1/orders with form-urlencoded returns 422 (CSRF protection)
# ===========================================================================


class TestCsrfProtection:
    """JSON Content-Type enforcement for state-changing endpoints."""

    async def test_form_encoded_rejected(self, app, db_path):
        """POST with application/x-www-form-urlencoded returns 422."""
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'lavender-dream', 1)",
            (sid,),
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, sid)
            resp = await c.post(
                "/v1/orders",
                content="customer_email=t%40t.com",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        assert resp.status_code == 422
