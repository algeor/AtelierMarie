"""Unit tests for the shipping_service orchestrator.

Covers task 3.2 of shipping-pricing (Phase A):
- free-shipping short-circuit returns 0¢ live quotes BEFORE any courier call
- cart weight is summed from DB `products.weight_grams × quantity` + packaging
- both couriers are fanned out for the approximate phase
- one courier up / one down yields independent per-quote provenance

The courier clients are patched at the module boundary so no HTTP happens.
"""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.constants import (
    FALLBACK_SHIPPING_CENTS,
    FREE_SHIPPING_THRESHOLD_CENTS,
    PACKAGING_WEIGHT_GRAMS,
)
from app.database import init_db
from app.models.shipping import ShippingQuote
from app.services import delivery_service, shipping_service

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "svc.db")
    init_db(path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    yield connection
    connection.close()


@pytest.fixture()
def session_id(conn):
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.commit()
    return sid


def _seed_product(conn, pid: str, weight_grams: int, price_cents: int = 1000) -> None:
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, weight_grams, is_active)"
        " VALUES (?, ?, ?, 100, ?, 1)",
        (pid, pid, price_cents, weight_grams),
    )
    conn.commit()


def _add_to_cart(conn, session_id: str, pid: str, quantity: int) -> None:
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_id, pid, quantity),
    )
    conn.commit()


# ===========================================================================
# cart_weight_grams
# ===========================================================================


class TestCartWeight:
    def test_sums_weight_times_quantity_plus_packaging(self, conn, session_id):
        _seed_product(conn, "a", weight_grams=300)
        _seed_product(conn, "b", weight_grams=500)
        _add_to_cart(conn, session_id, "a", 2)  # 600
        _add_to_cart(conn, session_id, "b", 1)  # 500
        assert (
            shipping_service.cart_weight_grams(conn, session_id)
            == 600 + 500 + PACKAGING_WEIGHT_GRAMS
        )

    def test_empty_cart_yields_only_packaging_buffer(self, conn, session_id):
        assert shipping_service.cart_weight_grams(conn, session_id) == PACKAGING_WEIGHT_GRAMS


# ===========================================================================
# calculate_quotes orchestration
# ===========================================================================


class TestFreeShippingShortCircuit:
    @pytest.mark.asyncio
    async def test_free_shipping_returns_zero_before_any_courier_call(self, monkeypatch):
        """Items ≥ €50 → 0¢ live quotes, and neither courier client is called."""
        speedy_called = False
        econt_called = False

        async def _speedy(**kwargs):
            nonlocal speedy_called
            speedy_called = True
            return ShippingQuote(courier="speedy", cents=999, price_source="live")

        async def _econt(**kwargs):
            nonlocal econt_called
            econt_called = True
            return ShippingQuote(courier="econt", cents=999, price_source="live")

        monkeypatch.setattr(shipping_service.speedy_client, "calculate", _speedy)
        monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)

        quotes = await shipping_service.calculate_quotes(
            couriers=["speedy", "econt"],
            method="office",
            city="София",
            office_id=None,
            address=None,
            weight_grams=1000,
            items_total_cents=FREE_SHIPPING_THRESHOLD_CENTS,
        )

        assert speedy_called is False
        assert econt_called is False
        assert len(quotes) == 2
        for q in quotes:
            assert q.cents == 0
            assert q.price_source == "live"
            assert q.is_fallback is False
            assert q.quoted_at is not None


class TestFanOut:
    @pytest.mark.asyncio
    async def test_both_couriers_returned_for_comparison(self, monkeypatch):
        async def _speedy(**kwargs):
            return ShippingQuote(courier="speedy", cents=650, price_source="live")

        async def _econt(**kwargs):
            return ShippingQuote(courier="econt", cents=590, price_source="live")

        monkeypatch.setattr(shipping_service.speedy_client, "calculate", _speedy)
        monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)

        quotes = await shipping_service.calculate_quotes(
            couriers=["speedy", "econt"],
            method="office",
            city="София",
            office_id=None,
            address=None,
            weight_grams=1000,
            items_total_cents=2000,
        )

        by_courier = {q.courier: q for q in quotes}
        assert by_courier["speedy"].cents == 650
        assert by_courier["econt"].cents == 590
        assert all(q.price_source == "live" for q in quotes)

    @pytest.mark.asyncio
    async def test_one_courier_up_one_down_independent_provenance(self, monkeypatch):
        """Speedy live, Econt degraded → each quote carries its own provenance."""

        async def _speedy(**kwargs):
            return ShippingQuote(courier="speedy", cents=650, price_source="live")

        async def _econt(**kwargs):
            return ShippingQuote(
                courier="econt",
                cents=FALLBACK_SHIPPING_CENTS,
                price_source="flat",
                is_fallback=True,
            )

        monkeypatch.setattr(shipping_service.speedy_client, "calculate", _speedy)
        monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)

        quotes = await shipping_service.calculate_quotes(
            couriers=["speedy", "econt"],
            method="office",
            city="София",
            office_id=None,
            address=None,
            weight_grams=1000,
            items_total_cents=2000,
        )

        by_courier = {q.courier: q for q in quotes}
        assert by_courier["speedy"].price_source == "live"
        assert by_courier["speedy"].is_fallback is False
        assert by_courier["econt"].price_source == "flat"
        assert by_courier["econt"].is_fallback is True
        assert by_courier["econt"].cents == FALLBACK_SHIPPING_CENTS

    @pytest.mark.asyncio
    async def test_exact_mode_single_courier(self, monkeypatch):
        async def _econt(**kwargs):
            # office_id is threaded through to the client in exact mode
            assert kwargs["recipient_office_id"] == "econt-sf-01"
            return ShippingQuote(courier="econt", cents=575, price_source="live")

        monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)

        quotes = await shipping_service.calculate_quotes(
            couriers=["econt"],
            method="office",
            city="София",
            office_id="econt-sf-01",
            address=None,
            weight_grams=1000,
            items_total_cents=2000,
        )
        assert len(quotes) == 1
        assert quotes[0].courier == "econt"
        assert quotes[0].cents == 575


# ===========================================================================
# Econt city translation (Latin → Bulgarian) before pricing
# ===========================================================================


class TestResolveCityBg:
    def test_latin_city_maps_to_bulgarian(self):
        # "Sofia" is the transliteration of "София" in the seeded office data.
        assert delivery_service.resolve_city_bg("econt", "Sofia") == "София"

    def test_latin_city_is_case_insensitive(self):
        assert delivery_service.resolve_city_bg("econt", "SOFIA") == "София"

    def test_bulgarian_city_passes_through(self):
        assert delivery_service.resolve_city_bg("econt", "София") == "София"

    def test_unknown_city_passes_through_unchanged(self):
        assert delivery_service.resolve_city_bg("econt", "Atlantis") == "Atlantis"


class TestEcontCityTranslation:
    @pytest.mark.asyncio
    async def test_office_mode_city_translated_to_bulgarian(self, monkeypatch):
        """A locale=en checkout sends a Latin city; Econt must receive Cyrillic."""
        seen: dict[str, str] = {}

        async def _econt(**kwargs):
            seen["recipient_city"] = kwargs["recipient_city"]
            return ShippingQuote(courier="econt", cents=590, price_source="live")

        monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)

        await shipping_service.calculate_quotes(
            couriers=["econt"],
            method="office",
            city="Sofia",
            office_id=None,
            address=None,
            weight_grams=1000,
            items_total_cents=2000,
        )

        assert seen["recipient_city"] == "София"

    @pytest.mark.asyncio
    async def test_door_mode_city_translated_without_mutating_shared_address(self, monkeypatch):
        """Door address city is translated for Econt but Speedy sees it unchanged."""
        from app.models.shipping import ShippingAddress

        econt_city: dict[str, str] = {}
        speedy_city: dict[str, str] = {}

        async def _econt(**kwargs):
            econt_city["city"] = kwargs["address"].city
            return ShippingQuote(courier="econt", cents=590, price_source="live")

        async def _speedy(**kwargs):
            speedy_city["city"] = kwargs["address"].city
            return ShippingQuote(courier="speedy", cents=650, price_source="live")

        monkeypatch.setattr(shipping_service.econt_client, "calculate", _econt)
        monkeypatch.setattr(shipping_service.speedy_client, "calculate", _speedy)

        address = ShippingAddress(
            courier="econt",
            city="Sofia",
            postal_code="1000",
            street="Vitosha",
        )

        await shipping_service.calculate_quotes(
            couriers=["econt", "speedy"],
            method="door",
            city="Sofia",
            office_id=None,
            address=address,
            weight_grams=1000,
            items_total_cents=2000,
        )

        assert econt_city["city"] == "София"
        assert speedy_city["city"] == "Sofia"  # untranslated, not mutated
        assert address.city == "Sofia"  # caller's instance untouched
