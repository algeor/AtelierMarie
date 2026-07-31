"""Structured delivery — checkout persistence + validation error tests.

Covers tasks 4.3, 4.4, 4.5 of shipping-courier-integration:

- 4.3: Office-delivery checkout persists delivery_method/courier/details.
  (The main happy path is already asserted in
  `tests/realapp/test_order_routes.py::TestCreateOrder::test_checkout_success_201`.
  This file adds JSON round-trip + cross-session read persistence coverage.)
- 4.4: Door-delivery checkout persists the full structured address.
- 4.5: Missing `delivery`, invalid method, and mismatched sub-object → 422.

Uses the realapp fixtures (`app`) plus locally-defined product seed / session /
client fixtures — mirrors the pattern in `test_order_routes.py`.
"""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture(autouse=True)
def _seed_products(db_path, app):
    """Seed products used by all checkout tests in this file."""
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
    """Session with pre-populated cart items."""
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
    """AsyncClient carrying the pre-seeded session cookie."""
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(settings.session_cookie_name, order_session_id)
        yield c


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

DELIVERY_OFFICE_ECONT_APT = {
    "method": "office",
    "office": {
        "courier": "econt",
        "office_id": "econt-34024",
        "office_name": "Бургас 24/7 Еконтомат- Автогара Запад",
        "office_type": "apt",
        "city": "Бургас",
        "phone": "+359888123456",
    },
}

DELIVERY_DOOR_FULL = {
    "method": "door",
    "door": {
        "courier": "econt",
        "city": "София",
        "postal_code": "1000",
        "street": "бул. Витоша 100",
        "building": "Б",
        "apartment": "12",
        "phone": "+359888123456",
    },
}

DELIVERY_DOOR_MINIMAL = {
    "method": "door",
    "door": {
        "courier": "speedy",
        "city": "Пловдив",
        "postal_code": "4000",
        "street": "ул. Главна 5",
        "phone": "+359888111222",
    },
}


class TestOfficeDeliveryPersistence:
    """4.3: office delivery — fields land correctly and survive GET round-trip."""

    async def test_office_delivery_locker(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT_APT},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["delivery_method"] == "office"
        assert data["delivery_courier"] == "econt"
        assert data["delivery_details"]["office_type"] == "apt"
        assert data["delivery_details"]["office_id"] == "econt-34024"

    async def test_office_delivery_survives_get_roundtrip(self, order_client):
        """POST then GET — Cyrillic details survive the JSON DB round-trip."""
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "t@t.com", "delivery": DELIVERY_OFFICE_ECONT},
        )
        assert resp.status_code == 201
        order_id = resp.json()["id"]

        get_resp = await order_client.get(f"/v1/orders/{order_id}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["delivery_method"] == "office"
        assert body["delivery_courier"] == "econt"
        # Cyrillic preserved through ensure_ascii=False JSON serialization
        assert body["delivery_details"]["office_name"] == "София"
        assert body["delivery_details"]["phone"] == "+359888123456"


class TestDoorDeliveryPersistence:
    """4.4: door delivery — full and minimal address forms persist."""

    async def test_door_delivery_full_address(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "t@t.com", "delivery": DELIVERY_DOOR_FULL},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["delivery_method"] == "door"
        assert data["delivery_courier"] == "econt"
        details = data["delivery_details"]
        assert details["city"] == "София"
        assert details["postal_code"] == "1000"
        assert details["street"] == "бул. Витоша 100"
        assert details["building"] == "Б"
        assert details["apartment"] == "12"
        assert details["phone"] == "+359888123456"

    async def test_door_delivery_minimal_address(self, order_client):
        """Optional building/apartment can be omitted."""
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "t@t.com", "delivery": DELIVERY_DOOR_MINIMAL},
        )
        assert resp.status_code == 201
        details = resp.json()["delivery_details"]
        assert details["city"] == "Пловдив"
        assert details.get("building") is None
        assert details.get("apartment") is None

    async def test_door_delivery_survives_get_roundtrip(self, order_client):
        resp = await order_client.post(
            "/v1/orders",
            json={"customer_email": "t@t.com", "delivery": DELIVERY_DOOR_FULL},
        )
        order_id = resp.json()["id"]

        get_resp = await order_client.get(f"/v1/orders/{order_id}")
        assert get_resp.status_code == 200
        details = get_resp.json()["delivery_details"]
        # Cyrillic address preserved
        assert details["street"] == "бул. Витоша 100"


class TestCheckoutDeliveryValidation:
    """4.5: /v1/orders request validation for structured delivery."""

    @pytest.mark.parametrize(
        "payload",
        [
            # missing delivery entirely
            {"customer_email": "t@t.com"},
            # invalid method literal
            {"customer_email": "t@t.com", "delivery": {"method": "pigeon"}},
            # office method but no office sub-object
            {"customer_email": "t@t.com", "delivery": {"method": "office"}},
            # door method but no door sub-object
            {"customer_email": "t@t.com", "delivery": {"method": "door"}},
            # office method with door sub-object (mutual-exclusion violation)
            {
                "customer_email": "t@t.com",
                "delivery": {
                    "method": "office",
                    "door": DELIVERY_DOOR_FULL["door"],
                },
            },
            # office with invalid courier
            {
                "customer_email": "t@t.com",
                "delivery": {
                    "method": "office",
                    "office": {
                        **DELIVERY_OFFICE_ECONT["office"],
                        "courier": "dhl",
                    },
                },
            },
            # office with invalid office_type
            {
                "customer_email": "t@t.com",
                "delivery": {
                    "method": "office",
                    "office": {
                        **DELIVERY_OFFICE_ECONT["office"],
                        "office_type": "warehouse",
                    },
                },
            },
            # office with invalid phone
            {
                "customer_email": "t@t.com",
                "delivery": {
                    "method": "office",
                    "office": {**DELIVERY_OFFICE_ECONT["office"], "phone": "abc"},
                },
            },
            # door missing required street
            {
                "customer_email": "t@t.com",
                "delivery": {
                    "method": "door",
                    "door": {
                        "courier": "econt",
                        "city": "София",
                        "postal_code": "1000",
                        "phone": "+359888123456",
                    },
                },
            },
        ],
    )
    async def test_invalid_delivery_returns_422(self, order_client, payload):
        resp = await order_client.post("/v1/orders", json=payload)
        assert resp.status_code == 422, f"expected 422, got {resp.status_code} for {payload}"

    async def test_nonexistent_office_id_returns_422(self, order_client):
        payload = {
            "customer_email": "t@t.com",
            "delivery": {
                "method": "office",
                "office": {
                    **DELIVERY_OFFICE_ECONT["office"],
                    "office_id": "econt-missing",
                },
            },
        }

        resp = await order_client.post("/v1/orders", json=payload)

        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "INVALID_DELIVERY_OFFICE"
        assert body["error"]["details"]["office_id"] == "econt-missing"
