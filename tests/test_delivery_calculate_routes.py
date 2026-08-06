"""Integration tests for `POST /v1/delivery/calculate`.

Covers task 3.3 of shipping-pricing (Phase A): approximate mode (both couriers),
exact mode (one courier + office_id), validation errors, and free-shipping
short-circuit. Courier clients are patched so no real HTTP is attempted.

Uses the module-scoped app/client (FakeSessionMiddleware) from the root conftest.
"""

import pytest

from app.models.shipping import ShippingQuote
from app.services import shipping_service


@pytest.fixture()
def cart_with_weight(db, session_id):
    """Seed one product (300g) and add 2 to the fake session's cart."""
    db.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, weight_grams, is_active)"
        " VALUES ('w-candle', 'W Candle', 1000, 50, 300, 1)",
    )
    db.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, 'w-candle', 2)",
        (session_id,),
    )
    db.commit()
    return session_id


@pytest.fixture()
def patch_couriers(monkeypatch):
    async def _speedy(**kwargs):
        return ShippingQuote(
            courier="speedy", cents=650, price_source="live", estimated_delivery_days=2
        )

    async def _econt(**kwargs):
        return ShippingQuote(
            courier="econt", cents=590, price_source="live", estimated_delivery_days=1
        )

    monkeypatch.setattr(shipping_service.speedy_client, "calculate", _speedy)
    monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)


class TestCalculateEndpoint:
    @pytest.mark.asyncio
    async def test_approximate_mode_both_couriers(self, client, cart_with_weight, patch_couriers):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "office",
                "city": "София",
                "items_total_cents": 2000,
                "couriers": ["speedy", "econt"],
            },
        )
        assert resp.status_code == 200
        quotes = resp.json()["quotes"]
        assert len(quotes) == 2
        by_courier = {q["courier"]: q for q in quotes}
        assert by_courier["speedy"]["cents"] == 650
        assert by_courier["econt"]["cents"] == 590
        assert all(q["price_source"] == "live" for q in quotes)

    @pytest.mark.asyncio
    async def test_exact_mode_single_courier(self, client, cart_with_weight, patch_couriers):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "office",
                "city": "София",
                "office_id": "speedy-sf-01",
                "items_total_cents": 2000,
                "couriers": ["speedy"],
            },
        )
        assert resp.status_code == 200
        quotes = resp.json()["quotes"]
        assert len(quotes) == 1
        assert quotes[0]["courier"] == "speedy"

    @pytest.mark.asyncio
    async def test_door_mode_without_phone(self, client, cart_with_weight, patch_couriers):
        # Regression: the preview address must NOT require a phone (a price
        # preview should never force the shopper to enter one). Before the
        # ShippingAddress split this 422'd on a missing address.phone.
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "door",
                "city": "София",
                "address": {
                    "courier": "econt",
                    "city": "София",
                    "postal_code": "1000",
                    "street": "бул. Витоша",
                    "building": "1",
                },
                "items_total_cents": 2000,
                "couriers": ["econt"],
            },
        )
        assert resp.status_code == 200
        quotes = resp.json()["quotes"]
        assert len(quotes) == 1
        assert quotes[0]["courier"] == "econt"

    @pytest.mark.asyncio
    async def test_door_mode_city_only_address(self, client, cart_with_weight, patch_couriers):
        # Only `city` is required on a preview address; street/postcode optional.
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "door",
                "city": "София",
                "address": {"courier": "econt", "city": "София"},
                "items_total_cents": 2000,
                "couriers": ["econt"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["quotes"][0]["courier"] == "econt"

    @pytest.mark.asyncio
    async def test_free_shipping_short_circuit(self, client, cart_with_weight, patch_couriers):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "office",
                "city": "София",
                "items_total_cents": 5000,
                "couriers": ["speedy", "econt"],
            },
        )
        assert resp.status_code == 200
        quotes = resp.json()["quotes"]
        assert all(q["cents"] == 0 for q in quotes)
        assert all(q["price_source"] == "live" for q in quotes)

    @pytest.mark.asyncio
    async def test_invalid_courier_rejected(self, client, cart_with_weight):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "office",
                "city": "София",
                "items_total_cents": 2000,
                "couriers": ["dhl"],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_method_rejected(self, client, cart_with_weight):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "drone",
                "city": "София",
                "items_total_cents": 2000,
                "couriers": ["speedy"],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_exact_mode_requires_single_courier(self, client, cart_with_weight):
        """office_id present but two couriers → model validation error (422)."""
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "office",
                "city": "София",
                "office_id": "speedy-sf-01",
                "items_total_cents": 2000,
                "couriers": ["speedy", "econt"],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_office_id_forbidden_for_door_method(self, client, cart_with_weight):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "door",
                "city": "София",
                "office_id": "speedy-sf-01",
                "items_total_cents": 2000,
                "couriers": ["speedy"],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_couriers_rejected(self, client, cart_with_weight):
        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "office",
                "city": "София",
                "items_total_cents": 2000,
                "couriers": [],
            },
        )
        assert resp.status_code == 422
