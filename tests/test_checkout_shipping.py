"""Order service checkout tests for shipping price + provenance (shipping-pricing).

Covers tasks 3.4–3.7:
- 3.4 valid shipping_cents persisted, in total_cents, provenance persisted
- 3.5 free-shipping enforcement forces 0 and normalizes provenance
- 3.6 range validation → InvalidShippingPriceError
- 3.7 legacy order rows default to shipping_cents=0, live, non-fallback
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.constants import INTERNAL_DELIVERY_CENTS, SHIPPING_CENTS_MAX
from app.models.delivery import DeliveryInfo, DeliveryInternal, DeliveryOffice
from app.services.order_service import (
    InvalidShippingPriceError,
    checkout,
    get_order,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def conn(db):
    return db


@pytest.fixture(autouse=True)
def _reset_delivery_settings(db):
    """Reset the ``delivery_settings`` singleton between tests.

    ``delivery_settings`` is a migration-seed table (never truncated by the root
    ``_clean_tables``), but ``TestFreeShipping`` disables couriers via
    ``_disable_courier_delivery`` and that state would otherwise leak into
    ``TestRangeValidation``, whose econt office checkouts then fail with
    ``DeliveryMethodUnavailableError``. Deleting the row lets the service
    re-create it with all-enabled defaults on the next read (Decision 15).
    """
    db.execute("DELETE FROM delivery_settings")
    db.commit()
    yield
    db.execute("DELETE FROM delivery_settings")
    db.commit()


@pytest.fixture()
def session_id(conn):
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (%s, %s, %s)",
        (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.commit()
    return sid


@pytest.fixture()
def delivery() -> DeliveryInfo:
    return DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier="econt",
            office_id="econt-1029",
            office_name="Sofia Center",
            office_type="office",
            city="София",
            phone="+359888123456",
        ),
    )


def _cart_below_threshold(conn, session_id):
    """One €18 product → items_total 1800 (< €50)."""
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
        " VALUES ('cheap', 'Cheap', 1800, 10, 1)"
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, 'cheap', 1)",
        (session_id,),
    )
    conn.commit()


def _cart_above_threshold(conn, session_id):
    """One €60 product → items_total 6000 (≥ €50)."""
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
        " VALUES ('pricey', 'Pricey', 6000, 10, 1)"
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, 'pricey', 1)",
        (session_id,),
    )
    conn.commit()


def _disable_courier_delivery(conn) -> None:
    conn.execute(
        """
        INSERT INTO delivery_settings (
            id, speedy_office_enabled, speedy_door_enabled,
            econt_office_enabled, econt_door_enabled,
            cod_enabled, card_enabled, bank_transfer_enabled, updated_at
        ) VALUES ('default', 0, 0, 0, 0, 1, 1, 1, %s)
        ON CONFLICT (id) DO UPDATE SET
            speedy_office_enabled = 0,
            speedy_door_enabled = 0,
            econt_office_enabled = 0,
            econt_door_enabled = 0,
            updated_at = EXCLUDED.updated_at
        """,
        (datetime.now(UTC).strftime(_DT_FMT),),
    )
    conn.commit()


class TestValidShipping:
    def test_shipping_persisted_and_in_total(self, conn, session_id, delivery):
        _cart_below_threshold(conn, session_id)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="t@example.com",
            delivery=delivery,
            shipping_cents=650,
            shipping_price_source="live",
            shipping_is_fallback=False,
            shipping_quoted_at="2026-07-28 10:00:00",
        )
        assert order["items_total_cents"] == 1800
        assert order["shipping_cents"] == 650
        assert order["total_cents"] == 2450
        assert order["shipping_price_source"] == "live"
        assert order["shipping_is_fallback"] is False

        # Provenance persisted to DB, survives a re-fetch.
        fetched = get_order(conn, order["id"], session_id)
        assert fetched["shipping_cents"] == 650
        assert fetched["total_cents"] == 2450
        assert fetched["shipping_price_source"] == "live"
        assert fetched["shipping_is_fallback"] is False
        assert fetched["shipping_quoted_at"] == "2026-07-28 10:00:00"

    def test_fallback_provenance_persisted(self, conn, session_id, delivery):
        _cart_below_threshold(conn, session_id)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="t@example.com",
            delivery=delivery,
            shipping_cents=500,
            shipping_price_source="flat",
            shipping_is_fallback=True,
            shipping_quoted_at="2026-07-28 10:00:00",
        )
        fetched = get_order(conn, order["id"], session_id)
        assert fetched["shipping_price_source"] == "flat"
        assert fetched["shipping_is_fallback"] is True


class TestFreeShippingEnforcement:
    def test_server_forces_zero_and_normalizes_provenance(self, conn, session_id, delivery):
        """Client sends non-zero flat/fallback but items ≥ €50 → server overrides."""
        _cart_above_threshold(conn, session_id)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="t@example.com",
            delivery=delivery,
            shipping_cents=650,
            shipping_price_source="flat",
            shipping_is_fallback=True,
            shipping_quoted_at="2026-07-28 10:00:00",
        )
        assert order["shipping_cents"] == 0
        assert order["total_cents"] == 6000
        assert order["shipping_price_source"] == "live"
        assert order["shipping_is_fallback"] is False
        assert order["shipping_quoted_at"] is None


class TestInternalDelivery:
    def test_internal_delivery_adds_fixed_charge_when_couriers_disabled(self, conn, session_id):
        _disable_courier_delivery(conn)
        _cart_below_threshold(conn, session_id)
        delivery = DeliveryInfo(
            method="internal",
            internal=DeliveryInternal(
                city="София",
                postal_code="1000",
                street="бул. Витоша 1",
                phone="+359888123456",
            ),
        )

        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="t@example.com",
            delivery=delivery,
            shipping_cents=0,
        )

        assert order["shipping_cents"] == INTERNAL_DELIVERY_CENTS
        assert order["total_cents"] == 1800 + INTERNAL_DELIVERY_CENTS
        assert order["shipping_price_source"] == "live"
        assert order["shipping_is_fallback"] is False
        assert order["delivery_method"] == "internal"
        assert order["delivery_courier"] is None
        assert order["delivery_details"]["handled_by"] == "atelier"

    def test_internal_delivery_is_free_above_threshold(self, conn, session_id):
        _disable_courier_delivery(conn)
        _cart_above_threshold(conn, session_id)
        delivery = DeliveryInfo(
            method="internal",
            internal=DeliveryInternal(
                city="София",
                postal_code="1000",
                street="бул. Витоша 1",
                phone="+359888123456",
            ),
        )

        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="t@example.com",
            delivery=delivery,
            shipping_cents=INTERNAL_DELIVERY_CENTS,
        )

        assert order["shipping_cents"] == 0
        assert order["total_cents"] == 6000
        assert order["shipping_price_source"] == "live"
        assert order["shipping_is_fallback"] is False


class TestRangeValidation:
    def test_negative_shipping_rejected(self, conn, session_id, delivery):
        _cart_below_threshold(conn, session_id)
        with pytest.raises(InvalidShippingPriceError):
            checkout(
                conn=conn,
                session_id=session_id,
                customer_email="t@example.com",
                delivery=delivery,
                shipping_cents=-1,
            )

    def test_over_max_shipping_rejected(self, conn, session_id, delivery):
        _cart_below_threshold(conn, session_id)
        with pytest.raises(InvalidShippingPriceError):
            checkout(
                conn=conn,
                session_id=session_id,
                customer_email="t@example.com",
                delivery=delivery,
                shipping_cents=SHIPPING_CENTS_MAX + 1,
            )

    def test_boundary_max_accepted(self, conn, session_id, delivery):
        _cart_below_threshold(conn, session_id)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="t@example.com",
            delivery=delivery,
            shipping_cents=SHIPPING_CENTS_MAX,
        )
        assert order["shipping_cents"] == SHIPPING_CENTS_MAX


class TestLegacyOrderRetrieval:
    def test_legacy_row_defaults(self, conn, session_id):
        """A row inserted without shipping columns reads back as 0 / live / non-fallback."""
        order_id = str(uuid.uuid4())
        now = datetime.now(UTC).strftime(_DT_FMT)
        # Insert bypassing the shipping columns → they take their DB defaults.
        conn.execute(
            "INSERT INTO orders (id, session_id, status, total_cents, customer_email,"
            " created_at, updated_at) VALUES (%s, %s, 'pending', 2500, 'l@example.com', %s, %s)",
            (order_id, session_id, now, now),
        )
        conn.commit()
        order = get_order(conn, order_id, session_id)
        assert order["shipping_cents"] == 0
        assert order["items_total_cents"] == 2500
        assert order["total_cents"] == 2500
        assert order["shipping_price_source"] == "live"
        assert order["shipping_is_fallback"] is False
