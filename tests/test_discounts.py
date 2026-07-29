"""Discount behavior tests — service validation, public API, cart, checkout.

Pure pricing math and window boundaries live in test_pricing.py; this file
covers the integrated paths (persistence, merge semantics, public exposure,
cart totals, and the critical checkout price snapshot).
"""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.database import init_db
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.models.products import CreateProductRequest
from app.services import cart_service, product_service
from app.services.order_service import checkout
from app.services.product_service import DiscountValidationError

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _ts(delta_days: float) -> str:
    """Canonical UTC timestamp offset from now by delta_days."""
    return (datetime.now(UTC) + timedelta(days=delta_days)).strftime(_DT_FMT)


@pytest.fixture()
def db_path(tmp_path) -> str:
    return str(tmp_path / "discounts.db")


@pytest.fixture(autouse=True)
def _clean_tables():
    """Shadow the conftest autouse fixture — function-scoped db_path starts fresh."""
    yield


@pytest.fixture(autouse=True)
def _init(db_path):
    init_db(db_path)
    yield


def _create(**overrides) -> dict:
    """Create a product through the validated request model + service."""
    base = {
        "id": "cand-" + uuid.uuid4().hex[:8],
        "name_en": "Candle",
        "price_cents": 3250,
        "stock": 50,
    }
    base.update(overrides)
    req = CreateProductRequest(**base)
    return product_service.create_product(req.model_dump())


# ---------------------------------------------------------------------------
# 10.1 Model / service validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_create_manual_discount_active(self):
        product = _create(discount_percent=20)
        assert product["discount_active"] is True
        assert product["effective_price_cents"] == 2600
        assert product["discount_percent"] == 20

    def test_percent_out_of_range_rejected(self):
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            CreateProductRequest(id="x", name_en="X", price_cents=1000, stock=1, discount_percent=0)
        with pytest.raises(pydantic.ValidationError):
            CreateProductRequest(
                id="x", name_en="X", price_cents=1000, stock=1, discount_percent=100
            )

    def test_inverted_window_rejected(self):
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            CreateProductRequest(
                id="x",
                name_en="X",
                price_cents=1000,
                stock=1,
                discount_percent=20,
                discount_starts_at=_ts(5),
                discount_ends_at=_ts(1),
            )

    def test_date_without_percent_rejected_on_create(self):
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            CreateProductRequest(
                id="x", name_en="X", price_cents=1000, stock=1, discount_starts_at=_ts(1)
            )

    def test_timezone_less_datetime_rejected(self):
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            CreateProductRequest(
                id="x",
                name_en="X",
                price_cents=1000,
                stock=1,
                discount_percent=20,
                discount_starts_at="2026-08-01T12:30:00",
            )

    def test_update_one_bound_on_existing_discount(self):
        product = _create(discount_percent=20, discount_starts_at=_ts(-1), discount_ends_at=_ts(10))
        pid = product["id"]
        # Change only the end bound — merge validation uses the persisted percent.
        new_end = _ts(20)
        updated = product_service.update_product(pid, {"discount_ends_at": new_end})
        assert updated["discount_percent"] == 20
        assert updated["discount_ends_at"] == new_end

    def test_update_date_only_without_percent_rejected(self):
        product = _create()  # no discount
        pid = product["id"]
        with pytest.raises(DiscountValidationError):
            product_service.update_product(pid, {"discount_starts_at": _ts(1)})

    def test_update_percent_null_clears_all_bounds(self):
        product = _create(discount_percent=20, discount_starts_at=_ts(-1), discount_ends_at=_ts(10))
        pid = product["id"]
        updated = product_service.update_product(pid, {"discount_percent": None})
        assert updated["discount_percent"] is None
        assert updated["discount_starts_at"] is None
        assert updated["discount_ends_at"] is None
        assert updated["effective_price_cents"] == updated["price_cents"]

    def test_update_invalid_percent_rejected(self):
        # 150 fails at the Pydantic model layer for the request; the service also
        # guards the merged value defensively.
        product = _create(discount_percent=20)
        pid = product["id"]
        with pytest.raises(DiscountValidationError):
            product_service.update_product(pid, {"discount_percent": 150})


# ---------------------------------------------------------------------------
# 10.2 / 10.3 Public API exposure + active-window
# ---------------------------------------------------------------------------


class TestPublicApi:
    def test_active_discount_exposes_effective_price(self):
        product = _create(discount_percent=20)
        pid = product["id"]
        public = product_service.get_product(pid)
        assert public["price_cents"] == 3250
        assert public["effective_price_cents"] == 2600
        assert public["discount_percent"] == 20
        assert public["discount_active"] is True
        # Window timestamps never leak publicly.
        assert "discount_starts_at" not in public
        assert "discount_ends_at" not in public

    def test_future_scheduled_discount_hidden(self):
        product = _create(discount_percent=20, discount_starts_at=_ts(5), discount_ends_at=_ts(10))
        pid = product["id"]
        public = product_service.get_product(pid)
        assert public["discount_active"] is False
        assert public["discount_percent"] is None
        assert public["effective_price_cents"] == public["price_cents"]

    def test_expired_discount_hidden(self):
        product = _create(
            discount_percent=20, discount_starts_at=_ts(-10), discount_ends_at=_ts(-1)
        )
        public = product_service.get_product(product["id"])
        assert public["discount_active"] is False
        assert public["effective_price_cents"] == public["price_cents"]


# ---------------------------------------------------------------------------
# 10.8 Price sorting by effective price
# ---------------------------------------------------------------------------


class TestPriceSort:
    def test_price_asc_uses_effective_price(self):
        # A: 4000 with active 50% off → effective 2000; B: 3000 no discount.
        _create(id="prod-a", price_cents=4000, discount_percent=50)
        _create(id="prod-b", price_cents=3000)
        products, _ = product_service.list_products(sort="price_asc")
        ids = [p["id"] for p in products]
        assert ids.index("prod-a") < ids.index("prod-b")

    def test_price_desc_uses_effective_price(self):
        _create(id="prod-a", price_cents=4000, discount_percent=50)  # eff 2000
        _create(id="prod-b", price_cents=3000)  # eff 3000
        products, _ = product_service.list_products(sort="price_desc")
        ids = [p["id"] for p in products]
        assert ids.index("prod-b") < ids.index("prod-a")


# ---------------------------------------------------------------------------
# Cart + checkout fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(db_path):
    connection = sqlite3.connect(db_path)
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


@pytest.fixture()
def delivery() -> DeliveryInfo:
    return DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier="econt",
            office_id="econt-1029",
            office_name="София",
            office_type="office",
            phone="+359888123456",
        ),
    )


def _add_to_cart(conn, session_id, product_id, quantity):
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_id, product_id, quantity),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# 10.4 Cart totals reflect effective price
# ---------------------------------------------------------------------------


class TestCartTotals:
    def test_cart_total_uses_effective_price(self, conn, session_id):
        _create(id="disc", price_cents=3250, discount_percent=20)  # eff 2600
        _add_to_cart(conn, session_id, "disc", 2)
        cart = cart_service.get_cart(conn, session_id)
        assert cart.items[0].product["effective_price_cents"] == 2600
        assert cart.items[0].product["discount_active"] is True
        assert cart.total_cents == 5200

    def test_cart_hides_inactive_scheduled_discount(self, conn, session_id):
        _create(
            id="sched",
            price_cents=3250,
            discount_percent=20,
            discount_starts_at=_ts(5),
            discount_ends_at=_ts(10),
        )
        _add_to_cart(conn, session_id, "sched", 1)
        cart = cart_service.get_cart(conn, session_id)
        product = cart.items[0].product
        assert product["discount_percent"] is None
        assert product["discount_active"] is False
        assert product["effective_price_cents"] == 3250
        assert cart.total_cents == 3250


# ---------------------------------------------------------------------------
# 10.5 / 10.6 / 10.7 Checkout snapshot
# ---------------------------------------------------------------------------


class TestCheckoutSnapshot:
    def test_checkout_snapshots_discounted_price(self, conn, session_id, delivery):
        _create(id="disc", price_cents=3250, discount_percent=20)  # eff 2600
        _add_to_cart(conn, session_id, "disc", 2)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="m@example.com",
            delivery=delivery,
        )
        conn.commit()
        item = order["items"][0]
        assert item["price_cents"] == 2600
        assert order["total_cents"] == 5200
        # The snapshot lands in order_items too.
        snap = conn.execute(
            "SELECT price_cents FROM order_items WHERE order_id = ? AND product_id = 'disc'",
            (order["id"],),
        ).fetchone()[0]
        assert snap == 2600

    def test_floor_clamp_one_cent_99_percent(self, conn, session_id, delivery):
        # 99% off a 1-cent product → clamped to 1, never 0, no CHECK violation.
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active, discount_percent)"
            " VALUES ('penny', 'Penny', 1, 5, 1, 99)"
        )
        conn.commit()
        _add_to_cart(conn, session_id, "penny", 1)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="m@example.com",
            delivery=delivery,
        )
        conn.commit()
        assert order["items"][0]["price_cents"] == 1
        assert order["total_cents"] == 1

    def test_expired_discount_charges_full_price(self, conn, session_id, delivery):
        # Discount window already ended → checkout charges the post-expiry price
        # (live pricing; the cart-vs-checkout window edge is accepted behavior).
        _create(
            id="expired",
            price_cents=3250,
            discount_percent=20,
            discount_starts_at=_ts(-10),
            discount_ends_at=_ts(-1),
        )
        _add_to_cart(conn, session_id, "expired", 1)
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="m@example.com",
            delivery=delivery,
        )
        conn.commit()
        assert order["items"][0]["price_cents"] == 3250
        assert order["total_cents"] == 3250
