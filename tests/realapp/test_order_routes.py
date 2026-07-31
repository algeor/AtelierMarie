"""Integration tests for order routes with TestClient."""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings

_DT_FMT = "%Y-%m-%d %H:%M:%S"

# Reusable structured-delivery block for /v1/orders POSTs. Kept as a module-
# level dict so the JSON body composes with `**DELIVERY` (or nested inline).
DELIVERY_OFFICE_ECONT = {
    "method": "office",
    "office": {
        "courier": "econt",
        "office_id": "1001",
        "office_name": "Sofia Center",
        "office_type": "office",
        "city": "София",
        "phone": "+359888123456",
    },
}

DELIVERY_DOOR_SPEEDY = {
    "method": "door",
    "door": {
        "courier": "speedy",
        "city": "София",
        "postal_code": "1000",
        "street": "Витоша",
        "building": "5",
        "phone": "+359888123456",
    },
}


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
            json={
                "customer_email": "marie@example.com",
                "customer_name": "Marie",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            resp = await c.post(
                "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
            )
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
            resp = await c.post(
                "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
            )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # 7.4: POST returns 422 for invalid email, overly long fields
    async def test_invalid_email_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders", json={"customer_email": "not-an-email", "delivery": DELIVERY_OFFICE_ECONT}
        )
        assert resp.status_code == 422

    # customer_email fallback to the logged-in user's account email.
    async def test_logged_in_omitted_email_uses_account_email(self, app, db_path):
        """A logged-in user who omits customer_email gets their account email snapshotted."""
        uid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (id, google_id, email) VALUES (?, ?, ?)",
            (uid, "g-" + uid, "account@example.com"),
        )
        conn.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (sid, uid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
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
            resp = await c.post("/v1/orders", json={"delivery": DELIVERY_OFFICE_ECONT})
        assert resp.status_code == 201
        assert resp.json()["customer_email"] == "account@example.com"

    async def test_logged_in_supplied_email_overrides_account_email(self, app, db_path):
        """An explicit customer_email wins over the account email (gift/work address)."""
        uid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (id, google_id, email) VALUES (?, ?, ?)",
            (uid, "g-" + uid, "account@example.com"),
        )
        conn.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (sid, uid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
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
                json={"customer_email": "gift@example.com", "delivery": DELIVERY_OFFICE_ECONT},
            )
        assert resp.status_code == 201
        assert resp.json()["customer_email"] == "gift@example.com"

    async def test_anonymous_omitted_email_422_email_required(self, order_client):
        """Anonymous checkout with no email is rejected with EMAIL_REQUIRED."""
        resp = await order_client.post("/v1/orders", json={"delivery": DELIVERY_OFFICE_ECONT})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "EMAIL_REQUIRED"

    async def test_overly_long_customer_name_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "ok@ok.com",
                "customer_name": "X" * 201,
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        assert resp.status_code == 422

    async def test_overly_long_notes_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "ok@ok.com",
                "notes": "X" * 2001,
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        assert resp.status_code == 422


# ===========================================================================
# 7.5: GET /v1/orders returns paginated list
# ===========================================================================


class TestListMyOrders:
    """Integration tests for GET /v1/orders."""

    async def test_list_orders_paginated(self, order_client):
        # Create an order first
        await order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )

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
            resp = await c.post(
                "/v1/orders", json={"customer_email": "a@a.com", "delivery": DELIVERY_OFFICE_ECONT}
            )
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
            resp = await c.post(
                "/v1/orders", json={"customer_email": "a@a.com", "delivery": DELIVERY_OFFICE_ECONT}
            )
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
        resp = await admin_order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )
        order_id = resp.json()["id"]

        # Try invalid transition: pending → shipped
        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"

    async def test_ship_without_tracking_returns_422(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )
        order_id = resp.json()["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "shipped"}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "TRACKING_REQUIRED"

    async def test_ship_with_tracking_autogenerates_url(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )
        order_id = resp.json()["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": "77", "tracking_carrier": "econt"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tracking_number"] == "77"
        assert data["tracking_carrier"] == "econt"
        assert data["tracking_url"] == "https://www.econt.com/services/track-shipment/77"


class TestAdminSpeedyCourierOperations:
    """Admin Speedy endpoints use real app state with a fake courier boundary."""

    async def _create_shipped_speedy_order(self, admin_order_client, monkeypatch) -> str:
        def fake_create_shipment_sync(**kwargs):
            assert kwargs["recipient_city"] == "София"
            assert kwargs["recipient_street"] == "Витоша"
            assert kwargs["recipient_phone"] == "+359888123456"
            return "63689182611"

        monkeypatch.setattr(
            "app.services.speedy_client.create_shipment_sync", fake_create_shipment_sync
        )
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "speedy@example.com",
                "customer_name": "Speedy Buyer",
                "delivery": DELIVERY_DOOR_SPEEDY,
            },
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 200

        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "shipped"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tracking_number"] == "63689182611"
        assert data["tracking_carrier"] == "speedy"
        return order_id

    async def test_speedy_label_and_track_roundtrip(self, admin_order_client, monkeypatch):
        async def fake_print_label(**kwargs):
            assert kwargs["tracking_number"] == "63689182611"
            return b"%PDF-1.4 smoke label"

        async def fake_track_shipment(**kwargs):
            assert kwargs["tracking_number"] == "63689182611"
            return "delivered"

        monkeypatch.setattr("app.routes.admin.print_label", fake_print_label)
        monkeypatch.setattr("app.routes.admin.track_shipment", fake_track_shipment)
        order_id = await self._create_shipped_speedy_order(admin_order_client, monkeypatch)

        label_resp = await admin_order_client.get(f"/v1/admin/orders/{order_id}/label")
        assert label_resp.status_code == 200
        assert label_resp.headers["content-type"] == "application/pdf"
        assert label_resp.content.startswith(b"%PDF")

        track_resp = await admin_order_client.post(f"/v1/admin/orders/{order_id}/track")
        assert track_resp.status_code == 200
        data = track_resp.json()
        assert data["status"] == "shipped"
        assert data["courier_status"] == "delivered"

    async def test_speedy_label_failure_returns_502(self, admin_order_client, monkeypatch):
        from app.services.speedy_client import LabelPrintError

        async def fail_print_label(**kwargs):
            raise LabelPrintError("label unavailable", context="print")

        monkeypatch.setattr("app.routes.admin.print_label", fail_print_label)
        order_id = await self._create_shipped_speedy_order(admin_order_client, monkeypatch)

        resp = await admin_order_client.get(f"/v1/admin/orders/{order_id}/label")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "LABEL_PRINT_FAILED"

    async def test_non_speedy_order_has_no_speedy_waybill(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )
        order_id = resp.json()["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": "77", "tracking_carrier": "econt"},
        )

        label_resp = await admin_order_client.get(f"/v1/admin/orders/{order_id}/label")
        track_resp = await admin_order_client.post(f"/v1/admin/orders/{order_id}/track")
        assert label_resp.status_code == 404
        assert track_resp.status_code == 404
        assert label_resp.json()["error"]["code"] == "NO_SPEEDY_WAYBILL"
        assert track_resp.json()["error"]["code"] == "NO_SPEEDY_WAYBILL"


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
        await admin_order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )

        resp = await admin_order_client.get("/v1/admin/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_admin_filter_by_status(self, admin_order_client):
        # Create an order (status: pending)
        await admin_order_client.post(
            "/v1/orders", json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT}
        )

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
                "notes": "Handle with care",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        order_id = resp.json()["id"]

        resp = await admin_order_client.get(f"/v1/admin/orders/{order_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_email"] == "t@t.com"
        assert data["customer_name"] == "Test"
        assert data["notes"] == "Handle with care"
        assert data["delivery_method"] == "office"
        assert data["delivery_courier"] == "econt"
        assert data["delivery_details"]["office_id"] == "1001"
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


# ===========================================================================
# 8.6: durable outbox — queued rows written in the order transaction; the
# sweeper's send path reads the DB on its own connection and reaches 'sent'.
# ===========================================================================


class _RecordingProvider:
    """In-memory provider double for the integration test (no network)."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, *, to, subject, body, reply_to=None, tags=None) -> str | None:
        self.sent.append({"to": to, "subject": subject, "tags": tags})
        return "msg-1"


class TestDurableOutboxIntegration:
    """Checkout + ship queue rows in the order txn; one sweep delivers them."""

    async def test_checkout_queues_placed_and_admin_rows(self, admin_order_client, db_path):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={"customer_email": "buyer@example.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT event, status FROM order_emails WHERE order_id = ? ORDER BY event",
            (order_id,),
        ).fetchall()
        conn.close()
        events = {r[0]: r[1] for r in rows}
        # Both queued in the same commit as the order (Decision 25).
        assert events["placed"] == "queued"
        assert events["admin_new_order"] == "queued"

    async def test_sweeper_delivers_queued_emails(self, admin_order_client, db_path):
        from app.config import get_settings
        from app.services.email_service import drain_email_outbox

        resp = await admin_order_client.post(
            "/v1/orders",
            json={"customer_email": "buyer@example.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        order_id = resp.json()["id"]

        provider = _RecordingProvider()
        # Drive one sweeper tick directly (the send path opens its own connection).
        drain_email_outbox(provider=provider, settings=get_settings())

        # The customer 'placed' email was delivered (admin skipped — no address).
        assert any(m["to"] == "buyer@example.com" for m in provider.sent)
        conn = sqlite3.connect(db_path)
        placed = conn.execute(
            "SELECT status FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order_id,),
        ).fetchone()[0]
        conn.close()
        assert placed == "sent"

    async def test_ship_queues_and_sends_shipped_email(self, admin_order_client, db_path):
        from app.config import get_settings
        from app.services.email_service import drain_email_outbox

        resp = await admin_order_client.post(
            "/v1/orders",
            json={"customer_email": "buyer@example.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        order_id = resp.json()["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": "77", "tracking_carrier": "econt"},
        )

        conn = sqlite3.connect(db_path)
        shipped_status = conn.execute(
            "SELECT status FROM order_emails WHERE order_id = ? AND event = 'shipped'",
            (order_id,),
        ).fetchone()[0]
        conn.close()
        assert shipped_status == "queued"

        provider = _RecordingProvider()
        drain_email_outbox(provider=provider, settings=get_settings())
        shipped_email = next(m for m in provider.sent if "shipped" in (m["tags"] or []))
        assert shipped_email["to"] == "buyer@example.com"

    async def test_confirmed_transition_queues_no_email(self, admin_order_client, db_path):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={"customer_email": "buyer@example.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        order_id = resp.json()["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        conn = sqlite3.connect(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'confirmed'",
            (order_id,),
        ).fetchone()[0]
        conn.close()
        assert count == 0


# ===========================================================================
# 12.1: GET /v1/admin/orders/{id}/emails — audit trail (admin-gated)
# ===========================================================================


class TestOrderEmailAudit:
    """Admin can read the order_emails send-attempt log for an order."""

    async def test_audit_lists_queued_rows(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={"customer_email": "buyer@example.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        order_id = resp.json()["id"]

        resp = await admin_order_client.get(f"/v1/admin/orders/{order_id}/emails")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == order_id
        events = {e["event"]: e["status"] for e in data["emails"]}
        assert events.get("placed") == "queued"
        assert events.get("admin_new_order") == "queued"

    async def test_audit_requires_admin(self, order_client):
        resp = await order_client.get("/v1/admin/orders/some-id/emails")
        assert resp.status_code == 401

    async def test_audit_unknown_order_404(self, admin_order_client):
        resp = await admin_order_client.get("/v1/admin/orders/does-not-exist/emails")
        assert resp.status_code == 404
