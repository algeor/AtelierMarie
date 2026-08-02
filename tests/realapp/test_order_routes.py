"""Integration tests for order routes with TestClient."""

import sqlite3
import sys
import types
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

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
        "office_id": "econt-1029",
        "office_name": "София",
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


def _set_payment_settings(
    db_path: str,
    *,
    card_payments_enabled: bool = False,
    pay_on_delivery_enabled: bool = True,
    pay_on_delivery_max_cents: int = 5000,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO site_settings (key, value, value_type, is_public)
        VALUES (?, ?, 'json', 1)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, is_public = 1
        """,
        [
            ("card_payments_enabled", "true" if card_payments_enabled else "false"),
            ("pay_on_delivery_enabled", "true" if pay_on_delivery_enabled else "false"),
            ("pay_on_delivery_max_cents", str(pay_on_delivery_max_cents)),
        ],
    )
    conn.commit()
    conn.close()


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
    _set_payment_settings(db_path, pay_on_delivery_enabled=True)


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
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, 'lavender-dream', 1)",
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
        assert data["total_cents"] == 2500
        assert len(data["items"]) == 1
        assert data["accounting_currency"] == "EUR"
        assert data["accounting_readiness_status"] == "review_required"

    async def test_checkout_accepts_invoice_profile_and_snapshots_accounting_settings(
        self, order_client, db_path
    ):
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO seller_legal_profile_versions (
                effective_date, reviewed, legal_name, default_currency
            ) VALUES ('2026-08-01', 1, 'Atelier Marie OOD', 'EUR')
            """
        )
        seller_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO vat_fiscal_settings_versions (
                effective_date, reviewed, vat_mode, fiscal_document_mode
            ) VALUES ('2026-08-01', 1, 'registered', 'external_reference')
            """
        )
        vat_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Business Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
                "invoice_profile": {
                    "customer_type": "business",
                    "legal_name": "Buyer OOD",
                    "vat_identification_number": "BG987654321",
                    "business_registration_number": "987654321",
                    "billing_address": "1 Business Street, Sofia",
                    "billing_country": "bg",
                    "invoice_email": "invoice@example.com",
                    "purchase_reference_note": "PO-42",
                },
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["invoice_profile"]["legal_name"] == "Buyer OOD"
        assert body["invoice_profile"]["billing_country"] == "BG"
        assert body["seller_legal_profile_version_id"] == seller_id
        assert body["vat_fiscal_settings_version_id"] == vat_id
        assert body["accounting_classification_state"] == "business_vat_id_provided"
        assert body["accounting_readiness_status"] == "ready"
        assert body["accounting_snapshot"]["invoice_profile"]["invoice_email"] == (
            "invoice@example.com"
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            """
            SELECT invoice_profile_json, accounting_snapshot_json
            FROM orders WHERE id = ?
            """,
            (body["id"],),
        ).fetchone()
        conn.close()
        assert '"legal_name": "Buyer OOD"' in row[0]
        assert '"seller_legal_profile_version_id": ' in row[1]

    async def test_invalid_invoice_email_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "marie@example.com",
                "customer_name": "Marie",
                "delivery": DELIVERY_OFFICE_ECONT,
                "invoice_profile": {
                    "customer_type": "business",
                    "legal_name": "Buyer OOD",
                    "billing_address": "1 Business Street, Sofia",
                    "billing_country": "BG",
                    "invoice_email": "not-an-email",
                },
            },
        )

        assert resp.status_code == 422

    async def test_card_unavailable_without_stripe_key(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "marie@example.com",
                "customer_name": "Marie",
                "delivery": DELIVERY_OFFICE_ECONT,
                "payment_method": "card",
            },
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "PAYMENT_METHOD_UNAVAILABLE"

    async def test_bank_transfer_unavailable_without_iban(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "marie@example.com",
                "customer_name": "Marie",
                "delivery": DELIVERY_OFFICE_ECONT,
                "payment_method": "bank_transfer",
            },
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "PAYMENT_METHOD_UNAVAILABLE"

    async def test_cod_above_cap_rejected(self, app, db_path):
        sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'lavender-dream', 2)",
            (sid,),
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'midnight-amber', 1)",
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
                json={
                    "customer_email": "marie@example.com",
                    "customer_name": "Marie",
                    "delivery": DELIVERY_OFFICE_ECONT,
                    "payment_method": "cod",
                },
            )

        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "PAY_ON_DELIVERY_LIMIT_EXCEEDED"
        assert body["error"]["details"] == {"total_cents": 8500, "max_cents": 5000}

    async def test_cod_disabled_by_payment_settings_rejected(self, app, db_path, order_session_id):
        _set_payment_settings(db_path, pay_on_delivery_enabled=False)

        settings = get_settings()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.cookies.set(settings.session_cookie_name, order_session_id)
            resp = await c.post(
                "/v1/orders",
                json={
                    "customer_email": "marie@example.com",
                    "customer_name": "Marie",
                    "delivery": DELIVERY_OFFICE_ECONT,
                    "payment_method": "cod",
                },
            )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "PAYMENT_METHOD_UNAVAILABLE"

    async def test_cod_rate_limit_returns_429(self, order_client, db_path, order_session_id):
        payload = {
            "customer_email": "marie@example.com",
            "customer_name": "Marie",
            "delivery": DELIVERY_OFFICE_ECONT,
            "payment_method": "cod",
        }

        first = await order_client.post("/v1/orders", json=payload)
        assert first.status_code == 201

        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'lavender-dream', 1)",
            (order_session_id,),
        )
        conn.commit()
        conn.close()

        second = await order_client.post("/v1/orders", json=payload)
        assert second.status_code == 201

        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'lavender-dream', 1)",
            (order_session_id,),
        )
        conn.commit()
        conn.close()

        third = await order_client.post("/v1/orders", json=payload)
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "RATE_LIMITED"

    async def test_card_checkout_returns_stripe_url(self, app, db_path, order_session_id):
        from app.config import Settings

        _set_payment_settings(
            db_path,
            card_payments_enabled=True,
            pay_on_delivery_enabled=True,
        )

        class FakeSession:
            id = "cs_route_card"
            url = "https://checkout.example/route-card"
            status = "open"
            payment_intent = None

        class FakeCheckoutSession:
            @staticmethod
            def create(**_kwargs):
                return FakeSession()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.checkout = types.SimpleNamespace(Session=FakeCheckoutSession)

        settings = get_settings()
        transport = ASGITransport(app=app)
        with (
            patch.dict(sys.modules, {"stripe": fake_stripe}),
            patch(
                "app.routes.orders.get_settings",
                return_value=Settings(
                    stripe_secret_key="sk_test_route_card",
                    stripe_webhook_secret="whsec_route_card",
                    stripe_success_url="https://shop.example/success/{order_id}",
                    stripe_cancel_url="https://shop.example/cancel/{order_id}",
                ),
            ),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                c.cookies.set(settings.session_cookie_name, order_session_id)
                resp = await c.post(
                    "/v1/orders",
                    json={
                        "customer_email": "marie@example.com",
                        "customer_name": "Marie",
                        "delivery": DELIVERY_OFFICE_ECONT,
                        "payment_method": "card",
                    },
                )

        assert resp.status_code == 201
        body = resp.json()
        assert body["order_number"].startswith("AM-")
        assert body["payment_method"] == "card"
        assert body["payment_method_label"] == "Card payment"
        assert body["payment_status"] == "pending"
        assert body["payment_status_label"] == "Payment pending"
        assert body["reserved_until"] is not None
        assert body["payment_return_token"]
        assert body["stripe_checkout_url"] == "https://checkout.example/route-card"

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
                "/v1/orders",
                json={
                    "customer_email": "t@t.com",
                    "customer_name": "Test Buyer",
                    "delivery": DELIVERY_OFFICE_ECONT,
                },
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
                "/v1/orders",
                json={
                    "customer_email": "t@t.com",
                    "customer_name": "Test Buyer",
                    "delivery": DELIVERY_OFFICE_ECONT,
                },
            )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # 7.4: POST returns 422 for invalid email, overly long fields
    async def test_invalid_email_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={
                "customer_email": "not-an-email",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            resp = await c.post(
                "/v1/orders",
                json={"customer_name": "Account Buyer", "delivery": DELIVERY_OFFICE_ECONT},
            )
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
                json={
                    "customer_email": "gift@example.com",
                    "customer_name": "Gift Buyer",
                    "delivery": DELIVERY_OFFICE_ECONT,
                },
            )
        assert resp.status_code == 201
        assert resp.json()["customer_email"] == "gift@example.com"

    async def test_anonymous_omitted_email_422_email_required(self, order_client):
        """Anonymous checkout with no email is rejected with EMAIL_REQUIRED."""
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_name": "Test Buyer", "delivery": DELIVERY_OFFICE_ECONT},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "EMAIL_REQUIRED"

    async def test_missing_customer_name_422(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "ok@ok.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        assert resp.status_code == 422

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
                "customer_name": "Test Buyer",
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
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
                "/v1/orders",
                json={
                    "customer_email": "a@a.com",
                    "customer_name": "Test Buyer",
                    "delivery": DELIVERY_OFFICE_ECONT,
                },
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
                "/v1/orders",
                json={
                    "customer_email": "a@a.com",
                    "customer_name": "Test Buyer",
                    "delivery": DELIVERY_OFFICE_ECONT,
                },
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
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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

    async def test_payment_review_order_cannot_ship(self, admin_order_client, db_path):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "review-ship@example.com",
                "customer_name": "Review Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        order_id = resp.json()["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE orders SET payment_method = 'card', payment_status = 'review_required' "
            "WHERE id = ?",
            (order_id,),
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": "77", "tracking_carrier": "econt"},
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "PAYMENT_REVIEW_REQUIRED"
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()
        assert row[0] == "confirmed"

    async def test_ship_with_tracking_autogenerates_url(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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


class TestAdminReturnCases:
    """Admin return endpoints drive state deliberately and keep stock audited."""

    async def _create_shipped_econt_order(self, admin_order_client) -> str:
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "return-route@example.com",
                "customer_name": "Return Route Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]
        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        assert resp.status_code == 200
        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": "77", "tracking_carrier": "econt"},
        )
        assert resp.status_code == 200
        return order_id

    async def test_create_uncollected_return_moves_order_and_appears_in_detail(
        self, admin_order_client, db_path
    ):
        order_id = await self._create_shipped_econt_order(admin_order_client)
        conn = sqlite3.connect(db_path)
        stock_after_checkout = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        conn.close()

        resp = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns",
            json={
                "reason": "not_picked_up",
                "status": "return_in_transit",
                "courier_return_fee_cents": 500,
                "notes": "Not collected from Econt office",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["reason"] == "not_picked_up"
        assert body["status"] == "return_in_transit"
        assert body["restock_decision"] == "pending"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        stock_now = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        event = conn.execute(
            "SELECT event_type, payload_json FROM order_return_events WHERE order_return_id = ?",
            (body["id"],),
        ).fetchone()
        conn.close()
        assert row["status"] == "return_in_transit"
        assert stock_now == stock_after_checkout
        assert event["event_type"] == "return_created"
        assert "not_picked_up" in event["payload_json"]

        detail = await admin_order_client.get(f"/v1/admin/orders/{order_id}")
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["return_cases"][0]["id"] == body["id"]
        assert detail_body["return_events"][0]["event_type"] == "return_created"
        assert detail_body["refund_records"] == []
        assert detail_body["cod_settlement"] is None

    async def test_invalid_return_transition_rolls_back_case_creation(
        self, admin_order_client, db_path
    ):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "invalid-return@example.com",
                "customer_name": "Invalid Return Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        resp = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns",
            json={"reason": "not_picked_up", "status": "return_in_transit"},
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"
        conn = sqlite3.connect(db_path)
        order_status = conn.execute(
            "SELECT status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()[0]
        return_count = conn.execute(
            "SELECT COUNT(*) FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchone()[0]
        event_count = conn.execute(
            "SELECT COUNT(*) FROM order_return_events WHERE order_id = ?",
            (order_id,),
        ).fetchone()[0]
        conn.close()
        assert order_status == "pending"
        assert return_count == 0
        assert event_count == 0

    async def test_receive_inspect_and_close_return_controls_stock_explicitly(
        self, admin_order_client, db_path
    ):
        order_id = await self._create_shipped_econt_order(admin_order_client)
        conn = sqlite3.connect(db_path)
        stock_after_checkout = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        conn.close()
        created = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns",
            json={"reason": "customer_return", "status": "return_in_transit"},
        )
        return_id = created.json()["id"]

        received = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns/{return_id}/receive"
        )
        assert received.status_code == 200
        assert received.json()["status"] == "received"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order_row = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        stock_after_receive = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        conn.close()
        assert order_row["status"] == "returned"
        assert stock_after_receive == stock_after_checkout

        inspected = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/returns/{return_id}/inspect",
            json={"restock_decision": "restock", "notes": "Unopened return"},
        )
        assert inspected.status_code == 200
        assert inspected.json()["status"] == "inspected"
        assert inspected.json()["restock_decision"] == "restock"
        conn = sqlite3.connect(db_path)
        stock_after_inspect = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        adjustment = conn.execute(
            "SELECT quantity, reason FROM inventory_adjustments WHERE order_return_id = ?",
            (return_id,),
        ).fetchone()
        conn.close()
        assert stock_after_inspect == stock_after_checkout + 1
        assert adjustment == (1, "return_restock")

        closed = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns/{return_id}/close"
        )
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"

    async def test_return_action_wrong_order_id_does_not_mutate_case(
        self, admin_order_client, db_path
    ):
        order_id = await self._create_shipped_econt_order(admin_order_client)
        created = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns",
            json={"reason": "customer_return", "status": "return_in_transit"},
        )
        return_id = created.json()["id"]

        resp = await admin_order_client.post(
            f"/v1/admin/orders/not-the-order/returns/{return_id}/receive"
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RETURN_CASE_NOT_FOUND"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        case = conn.execute(
            "SELECT status, received_at FROM order_returns WHERE id = ?",
            (return_id,),
        ).fetchone()
        order = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()
        assert case["status"] == "return_in_transit"
        assert case["received_at"] is None
        assert order["status"] == "return_in_transit"

    async def test_update_return_accounting_fields(self, admin_order_client):
        order_id = await self._create_shipped_econt_order(admin_order_client)
        created = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/returns",
            json={"reason": "damaged_by_courier", "status": "return_in_transit"},
        )
        return_id = created.json()["id"]

        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/returns/{return_id}/accounting",
            json={
                "courier_return_fee_cents": 650,
                "courier_claim_id": "CLM-123",
                "courier_claim_status": "filed",
                "courier_claim_amount_cents": 2500,
                "notes": "Manual claim record",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["courier_return_fee_cents"] == 650
        assert body["courier_claim_id"] == "CLM-123"
        assert body["courier_claim_status"] == "filed"

    async def test_cod_settlement_endpoint_clears_detail_review_flag(self, admin_order_client):
        resp = await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "cod-settle@example.com",
                "customer_name": "COD Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )
        order = resp.json()
        order_id = order["id"]
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "confirmed"}
        )
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped", "tracking_number": "77", "tracking_carrier": "econt"},
        )
        await admin_order_client.patch(
            f"/v1/admin/orders/{order_id}/status", json={"status": "delivered"}
        )

        detail = await admin_order_client.get(f"/v1/admin/orders/{order_id}")
        assert detail.json()["cod_settlement_required"] is True

        resp = await admin_order_client.post(
            f"/v1/admin/orders/{order_id}/cod-settlement",
            json={
                "amount_cents": order["total_cents"],
                "settlement_date": "2026-08-01",
                "courier_reference": "COD-123",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["mismatch_review"] is False
        detail = await admin_order_client.get(f"/v1/admin/orders/{order_id}")
        assert detail.json()["cod_settlement_required"] is False
        assert detail.json()["cod_settlement"]["courier_reference"] == "COD-123"

    async def test_return_action_requires_admin(self, order_client):
        resp = await order_client.post(
            "/v1/admin/orders/some-order/returns",
            json={"reason": "customer_return"},
        )
        assert resp.status_code == 401


class TestAdminSpeedyCourierOperations:
    """Admin Speedy endpoints use real app state with a fake courier boundary."""

    async def _create_shipped_speedy_order(self, admin_order_client, monkeypatch) -> str:
        async def fake_create_shipment(**kwargs):
            assert kwargs["recipient_city"] == "София"
            assert kwargs["recipient_street"] == "Витоша"
            assert kwargs["recipient_phone"] == "+359888123456"
            assert kwargs["weight_grams"] == 300
            return "63689182611"

        monkeypatch.setattr("app.services.speedy_client.create_shipment", fake_create_shipment)
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
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
        )

        resp = await admin_order_client.get("/v1/admin/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_admin_filter_by_payment_method(
        self, admin_order_client, db_path, order_session_id
    ):
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        checkout(
            conn,
            session_id=order_session_id,
            customer_email="card@example.com",
            customer_name="Card Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'lavender-dream', 1)",
            (order_session_id,),
        )
        conn.commit()
        checkout(
            conn,
            session_id=order_session_id,
            customer_email="cod@example.com",
            customer_name="COD Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="cod",
        )
        conn.close()

        resp = await admin_order_client.get("/v1/admin/orders?payment_method=card")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["payment_method"] == "card"
        assert body["items"][0]["payment_method_label"] == "Card payment"

    async def test_admin_filter_abandoned_payment_review_queue(
        self, admin_order_client, db_path, order_session_id
    ):
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        review_order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="review-card@example.com",
            customer_name="Review Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.execute(
            "UPDATE orders SET payment_status = 'review_required' WHERE id = ?",
            (review_order["id"],),
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) "
            "VALUES (?, 'lavender-dream', 1)",
            (order_session_id,),
        )
        conn.commit()
        checkout(
            conn,
            session_id=order_session_id,
            customer_email="pending-card@example.com",
            customer_name="Pending Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.close()

        resp = await admin_order_client.get("/v1/admin/orders?review_filter=abandoned_payment")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == review_order["id"]
        assert body["items"][0]["payment_status"] == "review_required"

    async def test_admin_review_filter_uncollected_refused(self, admin_order_client, db_path):
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO orders (id, session_id, status, total_cents, customer_email)
            VALUES (?, 'review-session', ?, 2500, ?)
            """,
            [
                ("uncollected-order", "shipped", "uncollected@example.com"),
                ("refused-order", "return_in_transit", "refused@example.com"),
                ("closed-uncollected-order", "returned", "closed-uncollected@example.com"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO order_returns (id, order_id, reason, source, status)
            VALUES (?, ?, ?, 'admin', ?)
            """,
            [
                ("return-uncollected", "uncollected-order", "not_picked_up", "requested"),
                ("return-refused", "refused-order", "refused_delivery", "return_in_transit"),
                ("return-closed", "closed-uncollected-order", "not_picked_up", "closed"),
            ],
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get("/v1/admin/orders?review_filter=uncollected_refused")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {"uncollected-order", "refused-order"}

    async def test_admin_review_filter_refund_pending(self, admin_order_client, db_path):
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO orders (
                id, session_id, status, total_cents, customer_email,
                payment_method, payment_status
            ) VALUES (?, 'review-session', 'delivered', 2500, ?, 'card', ?)
            """,
            [
                ("refund-status-order", "refund-status@example.com", "refund_pending"),
                ("refund-record-order", "refund-record@example.com", "paid"),
                ("refund-succeeded-order", "refund-succeeded@example.com", "paid"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO payment_refunds (id, order_id, provider, amount_cents, status)
            VALUES (?, ?, 'stripe', 1000, ?)
            """,
            [
                ("pending-refund", "refund-record-order", "pending"),
                ("succeeded-refund", "refund-succeeded-order", "succeeded"),
            ],
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get("/v1/admin/orders?review_filter=refund_pending")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {
            "refund-status-order",
            "refund-record-order",
        }

    async def test_admin_review_filter_inspection_pending(self, admin_order_client, db_path):
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO orders (id, session_id, status, total_cents, customer_email)
            VALUES (?, 'review-session', ?, 2500, ?)
            """,
            [
                ("inspection-order", "returned", "inspection@example.com"),
                ("in-transit-order", "return_in_transit", "in-transit@example.com"),
                ("restocked-order", "returned", "restocked@example.com"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO order_returns (
                id, order_id, reason, source, status, restock_decision
            ) VALUES (?, ?, 'customer_return', 'admin', ?, ?)
            """,
            [
                ("return-inspection", "inspection-order", "received", "pending"),
                ("return-in-transit", "in-transit-order", "return_in_transit", "pending"),
                ("return-restocked", "restocked-order", "inspected", "restock"),
            ],
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get("/v1/admin/orders?review_filter=inspection_pending")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == "inspection-order"

    async def test_admin_review_filter_courier_claim_follow_up(self, admin_order_client, db_path):
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO orders (id, session_id, status, total_cents, customer_email)
            VALUES (?, 'review-session', 'return_in_transit', 2500, ?)
            """,
            [
                ("claim-filed-order", "claim-filed@example.com"),
                ("claim-id-order", "claim-id@example.com"),
                ("claim-paid-order", "claim-paid@example.com"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO order_returns (
                id, order_id, reason, source, status,
                courier_claim_id, courier_claim_status
            ) VALUES (?, ?, 'damaged_by_courier', 'admin', 'return_in_transit', ?, ?)
            """,
            [
                ("return-claim-filed", "claim-filed-order", "CLM-1", "filed"),
                ("return-claim-id", "claim-id-order", "CLM-2", "none"),
                ("return-claim-paid", "claim-paid-order", "CLM-3", "paid"),
            ],
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get(
            "/v1/admin/orders?review_filter=courier_claim_follow_up"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {"claim-filed-order", "claim-id-order"}

    async def test_admin_review_filter_cod_settlement_pending(self, admin_order_client, db_path):
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO orders (
                id, session_id, status, total_cents, customer_email,
                payment_method, payment_status
            ) VALUES (?, 'review-session', ?, 2500, ?, ?, ?)
            """,
            [
                ("cod-pending-order", "delivered", "cod-pending@example.com", "cod", "paid"),
                ("cod-settled-order", "delivered", "cod-settled@example.com", "cod", "paid"),
                ("card-delivered-order", "delivered", "card-delivered@example.com", "card", "paid"),
            ],
        )
        conn.execute(
            """
            INSERT INTO cod_settlements (id, order_id, amount_cents, settlement_date)
            VALUES ('settled-cod', 'cod-settled-order', 2500, '2026-08-01')
            """
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get("/v1/admin/orders?review_filter=cod_settlement_pending")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == "cod-pending-order"

    async def test_admin_filter_by_status(self, admin_order_client):
        # Create an order (status: pending)
        await admin_order_client.post(
            "/v1/orders",
            json={
                "customer_email": "t@t.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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

    async def test_invalid_payment_status_422(self, admin_order_client):
        resp = await admin_order_client.get("/v1/admin/orders?payment_status=bogus")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "INVALID_PAYMENT_STATUS"
        assert body["error"]["details"] is None

    async def test_invalid_review_filter_422(self, admin_order_client):
        resp = await admin_order_client.get("/v1/admin/orders?review_filter=bogus")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "INVALID_REVIEW_FILTER"
        assert "uncollected_refused" in body["error"]["message"]


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
        assert data["delivery_details"]["office_id"] == "econt-1029"
        assert len(data["items"]) == 1

    async def test_admin_detail_includes_payment_timeline(
        self, admin_order_client, db_path, order_session_id
    ):
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import apply_manual_payment_action, checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="timeline@example.com",
            customer_name="Timeline Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="cod",
        )
        apply_manual_payment_action(
            conn,
            order["id"],
            "mark_collected",
            "Collected at delivery",
            admin_id="admin-1",
            admin_email="owner@example.com",
            request_id="req-timeline",
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get(f"/v1/admin/orders/{order['id']}")

        assert resp.status_code == 200
        events = resp.json()["payment_events"]
        assert len(events) == 1
        assert events[0]["event_type"] == "manual_mark_collected"
        assert events[0]["admin_note"] == "Collected at delivery"
        assert events[0]["request_id"] == "req-timeline"

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

    async def test_stripe_retry_form_encoded_rejected(self, app, db_path):
        """Retry payment endpoint uses the same JSON content-type guard."""
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
                "/v1/orders/order-1/stripe-session",
                content="retry=true",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_CONTENT_TYPE"

    async def test_stripe_retry_wrong_session_rejected(self, app, db_path, order_session_id):
        """Retry payment endpoint must not expose another session's card order."""
        from app.config import Settings
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="buyer@example.com",
            customer_name="Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        other_sid = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (other_sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        transport = ASGITransport(app=app)
        with patch(
            "app.routes.orders.get_settings",
            return_value=Settings(
                stripe_secret_key="sk_test_retry",
                stripe_success_url="https://shop.example/success",
                stripe_cancel_url="https://shop.example/cancel",
            ),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                c.cookies.set(settings.session_cookie_name, other_sid)
                resp = await c.post(
                    f"/v1/orders/{order['id']}/stripe-session",
                    json={"payment_return_token": order["payment_return_token"]},
                )

        assert resp.status_code == 404

    async def test_stripe_retry_wrong_token_does_not_consume_rate_limit(
        self, app, db_path, order_session_id
    ):
        """Bad retry tokens must not burn the fresh Stripe-session budget."""
        from app.config import Settings
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        _set_payment_settings(
            db_path,
            card_payments_enabled=True,
            pay_on_delivery_enabled=True,
        )
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="buyer@example.com",
            customer_name="Buyer",
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.commit()
        conn.close()

        settings = get_settings()
        transport = ASGITransport(app=app)
        with patch(
            "app.routes.orders.get_settings",
            return_value=Settings(
                stripe_secret_key="sk_test_retry",
                stripe_webhook_secret="whsec_retry",
                stripe_success_url="https://shop.example/success",
                stripe_cancel_url="https://shop.example/cancel",
            ),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                c.cookies.set(settings.session_cookie_name, order_session_id)
                resp = await c.post(
                    f"/v1/orders/{order['id']}/stripe-session",
                    json={"payment_return_token": "wrong-token"},
                )

        assert resp.status_code == 404
        conn = sqlite3.connect(db_path)
        count = conn.execute(
            """
            SELECT COUNT(*) FROM payment_rate_limit_events
            WHERE action = 'stripe_session_create'
            """
        ).fetchone()[0]
        conn.close()
        assert count == 0


class TestAdminMarkPaymentPaid:
    async def test_bank_transfer_paid_queues_one_placed_email(
        self, admin_order_client, db_path, order_session_id
    ):
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="buyer@example.com",
            customer_name=None,
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="bank_transfer",
        )
        conn.close()

        resp = await admin_order_client.patch(
            f"/v1/admin/orders/{order['id']}/payment",
            json={"payment_status": "paid"},
        )
        assert resp.status_code == 200

        conn = sqlite3.connect(db_path)
        placed_count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()[0]
        conn.close()
        assert placed_count == 1


class TestAdminManualPaymentActions:
    async def test_mark_review_uses_review_required_status_and_writes_event(
        self, admin_order_client, db_path, order_session_id
    ):
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="review@example.com",
            customer_name=None,
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.close()

        resp = await admin_order_client.post(
            f"/v1/admin/orders/{order['id']}/payment-actions",
            json={"action": "mark_review", "note": "Late Stripe success after expiry"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["payment_status"] == "review_required"

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        event = conn.execute(
            "SELECT event_type, provider_status, admin_note, details "
            "FROM payment_events WHERE order_id = ?",
            (order["id"],),
        ).fetchone()
        conn.close()
        assert event["event_type"] == "manual_mark_review"
        assert event["provider_status"] == "review_required"
        assert event["admin_note"] == "Late Stripe success after expiry"
        assert '"current_vocabulary":true' in event["details"]

    async def test_blank_note_rejected_without_mutation(
        self, admin_order_client, db_path, order_session_id
    ):
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="blank-note@example.com",
            customer_name=None,
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.close()

        resp = await admin_order_client.post(
            f"/v1/admin/orders/{order['id']}/payment-actions",
            json={"action": "mark_review", "note": "   "},
        )

        assert resp.status_code == 422
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT payment_status FROM orders WHERE id = ?",
            (order["id"],),
        ).fetchone()
        event_count = conn.execute(
            "SELECT COUNT(*) FROM payment_events WHERE order_id = ?",
            (order["id"],),
        ).fetchone()[0]
        conn.close()
        assert row[0] == "pending"
        assert event_count == 0


class TestAdminStripeRefunds:
    async def test_admin_creates_partial_stripe_refund(
        self, admin_order_client, db_path, order_session_id, monkeypatch
    ):
        import sys
        import types

        from app.config import Settings
        from app.models.delivery import DeliveryInfo
        from app.services.order_service import checkout

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        order = checkout(
            conn,
            session_id=order_session_id,
            customer_email="refund@example.com",
            customer_name=None,
            delivery=DeliveryInfo.model_validate(DELIVERY_OFFICE_ECONT),
            notes=None,
            payment_method="card",
        )
        conn.execute(
            """
            UPDATE orders
            SET payment_status = 'paid', stripe_payment_intent_id = 'pi_route_refund'
            WHERE id = ?
            """,
            (order["id"],),
        )
        conn.execute(
            """
            UPDATE payments
            SET provider_status = 'paid', stripe_payment_intent_id = 'pi_route_refund'
            WHERE order_id = ? AND provider = 'stripe'
            """,
            (order["id"],),
        )
        conn.commit()
        conn.close()

        calls: list[dict] = []

        class FakeRefund:
            id = "re_route_refund"
            status = "pending"

        class FakeRefundAPI:
            @staticmethod
            def create(**kwargs):
                calls.append(kwargs)
                return FakeRefund()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.Refund = FakeRefundAPI
        monkeypatch.setitem(sys.modules, "stripe", fake_stripe)
        monkeypatch.setattr(
            "app.routes.admin.get_settings",
            lambda: Settings(stripe_secret_key="sk_test_refund"),
        )

        resp = await admin_order_client.post(
            f"/v1/admin/orders/{order['id']}/refunds",
            json={"amount_cents": 50, "idempotency_key": "route-refund-1"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["amount_cents"] == 50
        assert body["status"] == "pending"
        assert body["provider_refund_id"] == "re_route_refund"
        assert calls[0]["payment_intent"] == "pi_route_refund"
        assert calls[0]["amount"] == 50


class TestAdminAlerts:
    async def test_admin_lists_unread_alerts(self, admin_order_client, db_path):
        from app.services.admin_alert_service import create_admin_alert

        conn = sqlite3.connect(db_path)
        create_admin_alert(
            conn,
            alert_type="payment_requires_review",
            title="Payment review required",
            message="Late Stripe success arrived after expiry.",
            source="stripe",
            details={"payment_intent_id": "pi_alert"},
        )
        conn.commit()
        conn.close()

        resp = await admin_order_client.get("/v1/admin/alerts?unread_only=true")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["alerts"][0]["alert_type"] == "payment_requires_review"
        assert body["alerts"][0]["details"]["payment_intent_id"] == "pi_alert"


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
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Test Buyer",
                "delivery": DELIVERY_OFFICE_ECONT,
            },
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
