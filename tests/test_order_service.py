"""Unit tests for the order service layer."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.database import init_db
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.services.order_service import (
    EmptyCartError,
    InsufficientStockError,
    InvalidDeliveryOfficeError,
    InvalidStateTransitionError,
    OrderNotFoundError,
    PaymentReviewRequiredError,
    ProductUnavailableError,
    TrackingRequiredError,
    checkout,
    get_order,
    list_orders,
    update_status,
    update_status_async,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


# --- Function-scoped override ---


@pytest.fixture()
def db_path(tmp_path) -> str:
    """Function-scoped DB path for order service tests."""
    return str(tmp_path / "test.db")


@pytest.fixture(autouse=True)
def _clean_tables():
    """No-op: function-scoped db_path means each test starts fresh."""
    yield


@pytest.fixture()
def delivery() -> DeliveryInfo:
    """Reusable office-pickup delivery payload for checkout calls."""
    return DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier="econt",
            office_id="econt-1029",
            office_name="София",
            office_type="office",
            city="София",
            phone="+359888123456",
        ),
    )


@pytest.fixture()
def conn(db_path):
    """Return a raw sqlite3 connection with schema initialized."""
    init_db(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    yield connection
    connection.close()


@pytest.fixture()
def session_a(conn):
    """Create and return a session ID."""
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.commit()
    return sid


@pytest.fixture()
def session_b(conn):
    """Create a second session ID."""
    sid = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.commit()
    return sid


@pytest.fixture()
def products(conn):
    """Insert test products and return their data."""
    products_data = [
        ("lavender-dream", "Lavender Dream", 2500, 10),
        ("midnight-amber", "Midnight Amber", 3500, 5),
        ("vanilla-brulee", "Vanilla Brûlée", 1800, 1),
    ]
    for pid, name, price, stock in products_data:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, 1)",
            (pid, name, price, stock),
        )
    conn.commit()
    return products_data


@pytest.fixture()
def cart_with_items(conn, session_a, products):
    """Add items to session_a's cart."""
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_a, "lavender-dream", 2),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_a, "midnight-amber", 1),
    )
    conn.commit()
    return session_a


# ===========================================================================
# 4. Tests — Checkout Flow
# ===========================================================================


class TestCheckoutSuccess:
    """4.2: Successful checkout creates order, snapshots prices, decrements stock, clears cart."""

    def test_successful_checkout(self, conn, cart_with_items, products, delivery):
        session_id = cart_with_items
        order = checkout(
            conn=conn,
            session_id=session_id,
            customer_email="marie@example.com",
            customer_name="Marie",
            delivery=delivery,
        )
        conn.commit()

        # Order created
        assert order["status"] == "pending"
        assert order["customer_email"] == "marie@example.com"
        assert order["customer_name"] == "Marie"
        assert order["delivery_method"] == "office"
        assert order["delivery_courier"] == "econt"
        assert order["delivery_details"]["office_id"] == "econt-1029"
        assert len(order["items"]) == 2

        # Price snapshots correct
        lavender_item = next(i for i in order["items"] if i["product_id"] == "lavender-dream")
        amber_item = next(i for i in order["items"] if i["product_id"] == "midnight-amber")
        assert lavender_item["price_cents"] == 2500
        assert lavender_item["quantity"] == 2
        assert amber_item["price_cents"] == 3500
        assert amber_item["quantity"] == 1

        # total_cents = sum(price * qty)
        expected_total = 2500 * 2 + 3500 * 1
        assert order["total_cents"] == expected_total

        # Stock decremented
        lavender_stock = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        amber_stock = conn.execute(
            "SELECT stock FROM products WHERE id = 'midnight-amber'"
        ).fetchone()[0]
        assert lavender_stock == 8  # 10 - 2
        assert amber_stock == 4  # 5 - 1

        # Cart cleared
        cart_count = conn.execute(
            "SELECT COUNT(*) FROM cart_items WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        assert cart_count == 0

    def test_econt_office_code_is_taken_from_catalog_not_client(
        self, conn, cart_with_items, products
    ):
        delivery = DeliveryInfo(
            method="office",
            office=DeliveryOffice(
                courier="econt",
                office_id="econt-1029",
                office_code="wrong-client-code",
                office_name="София",
                office_type="office",
                city="София",
                phone="+359888123456",
            ),
        )

        order = checkout(
            conn=conn,
            session_id=cart_with_items,
            customer_email="marie@example.com",
            customer_name="Marie",
            delivery=delivery,
        )

        assert order["delivery_details"]["office_code"] == "1127"

    def test_econt_office_checkout_rejects_catalog_office_without_native_code(
        self, conn, cart_with_items, products, delivery, monkeypatch
    ):
        def fake_get_office(courier, office_id, *, locale="bg"):
            assert courier == "econt"
            assert office_id == "econt-1029"
            return {
                "id": office_id,
                "code": None,
                "name": "София",
                "type": "office",
                "city": "София",
                "address": "ул. Тест 1",
                "working_hours": "09:00-18:00",
            }

        monkeypatch.setattr(
            "app.services.order_service.delivery_service.get_office",
            fake_get_office,
        )

        with pytest.raises(InvalidDeliveryOfficeError) as exc_info:
            checkout(
                conn=conn,
                session_id=cart_with_items,
                customer_email="marie@example.com",
                customer_name="Marie",
                delivery=delivery,
            )

        assert exc_info.value.reason == "office_code required for Econt office delivery"


class TestCheckoutEmptyCart:
    """4.3: Checkout with empty cart raises EmptyCartError."""

    def test_empty_cart_raises(self, conn, session_a, products, delivery):
        with pytest.raises(EmptyCartError):
            checkout(
                conn=conn,
                session_id=session_a,
                customer_email="test@example.com",
                delivery=delivery,
            )


class TestCheckoutInsufficientStock:
    """4.4: Checkout with insufficient stock raises InsufficientStockError."""

    def test_insufficient_stock_raises(self, conn, session_a, products, delivery):
        # Add 6 units but only 5 in stock
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "midnight-amber", 6),
        )
        conn.commit()

        with pytest.raises(InsufficientStockError) as exc_info:
            checkout(
                conn=conn,
                session_id=session_a,
                customer_email="test@example.com",
                delivery=delivery,
            )

        assert exc_info.value.failures[0]["available"] == 5
        assert exc_info.value.failures[0]["requested"] == 6

        # Cart unchanged
        cart = conn.execute(
            "SELECT quantity FROM cart_items "
            "WHERE session_id = ? AND product_id = 'midnight-amber'",
            (session_a,),
        ).fetchone()
        assert cart[0] == 6

        # Stock unchanged
        stock = conn.execute("SELECT stock FROM products WHERE id = 'midnight-amber'").fetchone()[0]
        assert stock == 5


class TestCheckoutDeactivatedProduct:
    """4.5: Checkout with deactivated product raises ProductUnavailableError."""

    def test_deactivated_product_raises(self, conn, session_a, products, delivery):
        # Deactivate a product
        conn.execute("UPDATE products SET is_active = 0 WHERE id = 'lavender-dream'")
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "lavender-dream", 1),
        )
        conn.commit()

        with pytest.raises(ProductUnavailableError) as exc_info:
            checkout(
                conn=conn,
                session_id=session_a,
                customer_email="test@example.com",
                delivery=delivery,
            )

        assert exc_info.value.failures[0]["product_id"] == "lavender-dream"

        # Cart unchanged
        cart = conn.execute(
            "SELECT COUNT(*) FROM cart_items WHERE session_id = ?", (session_a,)
        ).fetchone()[0]
        assert cart == 1

        # Stock unchanged
        stock = conn.execute("SELECT stock FROM products WHERE id = 'lavender-dream'").fetchone()[0]
        assert stock == 10


class TestCheckoutMultipleFailures:
    """4.5b: Checkout with MULTIPLE failing items returns ALL failures."""

    def test_multiple_stock_failures(self, conn, session_a, products, delivery):
        # Both products have insufficient stock for requested quantities
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "midnight-amber", 6),  # only 5 in stock
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "vanilla-brulee", 2),  # only 1 in stock
        )
        conn.commit()

        with pytest.raises(InsufficientStockError) as exc_info:
            checkout(
                conn=conn,
                session_id=session_a,
                customer_email="test@example.com",
                delivery=delivery,
            )

        # Both failures reported
        product_ids = [f["product_id"] for f in exc_info.value.failures]
        assert "midnight-amber" in product_ids
        assert "vanilla-brulee" in product_ids


class TestCheckoutIntegrityConstraint:
    """4.6: CHECK constraint defense-in-depth raises InsufficientStockError."""

    def test_integrity_error_on_stock_decrement(self, conn, session_a, products, delivery):
        # Set stock to exactly 1, put 1 in cart
        conn.execute("UPDATE products SET stock = 1 WHERE id = 'lavender-dream'")
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "lavender-dream", 1),
        )
        conn.commit()

        # Manually decrement stock to 0 AFTER the cart was loaded but before checkout's
        # stock UPDATE runs — simulate a race condition. We do this by setting stock=0 directly.
        conn.execute("UPDATE products SET stock = 0 WHERE id = 'lavender-dream'")
        conn.commit()

        # Now checkout will try to decrement from 0, triggering CHECK constraint
        with pytest.raises(InsufficientStockError):
            checkout(
                conn=conn,
                session_id=session_a,
                customer_email="test@example.com",
                delivery=delivery,
            )


class TestPriceSnapshotImmutability:
    """4.7: Product price change after checkout does not affect existing order."""

    def test_price_change_after_checkout(self, conn, cart_with_items, delivery):
        session_id = cart_with_items
        order = checkout(
            conn=conn, session_id=session_id, customer_email="test@example.com", delivery=delivery
        )
        conn.commit()

        original_price = next(
            i["price_cents"] for i in order["items"] if i["product_id"] == "lavender-dream"
        )

        # Change product price
        conn.execute("UPDATE products SET price_cents = 9999 WHERE id = 'lavender-dream'")
        conn.commit()

        # Order item still has original price
        item_price = conn.execute(
            "SELECT price_cents FROM order_items "
            "WHERE order_id = ? AND product_id = 'lavender-dream'",
            (order["id"],),
        ).fetchone()[0]
        assert item_price == original_price
        assert item_price == 2500


class TestOrderIdFormat:
    """4.8: Created order ID matches UUID v4 format."""

    def test_order_id_is_uuid4(self, conn, cart_with_items, delivery):
        order = checkout(
            conn=conn,
            session_id=cart_with_items,
            customer_email="test@example.com",
            delivery=delivery,
        )
        conn.commit()

        # Validate UUID v4 format
        parsed = uuid.UUID(order["id"], version=4)
        assert str(parsed) == order["id"]


class TestTotalCentsServerComputed:
    """4.9: total_cents is computed server-side as sum(price_cents × quantity)."""

    def test_total_computed_correctly(self, conn, cart_with_items, delivery):
        order = checkout(
            conn=conn,
            session_id=cart_with_items,
            customer_email="test@example.com",
            delivery=delivery,
        )
        conn.commit()

        expected = sum(item["price_cents"] * item["quantity"] for item in order["items"])
        assert order["total_cents"] == expected
        assert order["total_cents"] == 2500 * 2 + 3500 * 1


class TestConcurrentCheckoutLastUnit:
    """4.10: Two sessions for last unit — one succeeds, one fails."""

    def test_last_unit_race(self, conn, session_a, session_b, products, delivery):
        # Both sessions have the last unit of vanilla-brulee (stock=1)
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "vanilla-brulee", 1),
        )
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_b, "vanilla-brulee", 1),
        )
        conn.commit()

        # First checkout succeeds
        order = checkout(
            conn=conn, session_id=session_a, customer_email="a@example.com", delivery=delivery
        )
        conn.commit()
        assert order["status"] == "pending"

        # Second checkout fails — stock is now 0
        with pytest.raises(InsufficientStockError):
            checkout(
                conn=conn, session_id=session_b, customer_email="b@example.com", delivery=delivery
            )

        # Stock is 0
        stock = conn.execute("SELECT stock FROM products WHERE id = 'vanilla-brulee'").fetchone()[0]
        assert stock == 0


# ===========================================================================
# 5. Tests — Order Management
# ===========================================================================


class TestListOrders:
    """5.1: list_orders returns only orders belonging to session/user, sorted DESC."""

    def test_list_orders_session_only(self, conn, cart_with_items, session_b, products, delivery):
        session_id = cart_with_items
        # Create an order for session_a
        checkout(
            conn=conn, session_id=session_id, customer_email="a@example.com", delivery=delivery
        )
        conn.commit()

        # Add cart for session_b and create order
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_b, "lavender-dream", 1),
        )
        conn.commit()
        checkout(conn=conn, session_id=session_b, customer_email="b@example.com", delivery=delivery)
        conn.commit()

        # list_orders for session_a should only show 1 order
        result = list_orders(conn=conn, session_id=session_id)
        assert result["total"] == 1
        assert result["items"][0]["session_id"] == session_id

    def test_list_orders_by_user_id_across_sessions(
        self, conn, session_a, session_b, products, delivery
    ):
        user_id = "user-123"
        # Link both sessions to same user
        conn.execute(
            "INSERT INTO users (id, google_id, email) VALUES (?, ?, ?)",
            (user_id, "g-123", "user@example.com"),
        )
        conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user_id, session_a))
        conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user_id, session_b))
        conn.commit()

        # Create orders from different sessions
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "lavender-dream", 1),
        )
        conn.commit()
        checkout(
            conn=conn,
            session_id=session_a,
            customer_email="u@test.com",
            user_id=user_id,
            delivery=delivery,
        )
        conn.commit()

        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_b, "midnight-amber", 1),
        )
        conn.commit()
        checkout(
            conn=conn,
            session_id=session_b,
            customer_email="u@test.com",
            user_id=user_id,
            delivery=delivery,
        )
        conn.commit()

        # list_orders by user_id returns both
        result = list_orders(conn=conn, session_id=session_a, user_id=user_id)
        assert result["total"] == 2

    def test_list_orders_sorted_desc(self, conn, session_a, products):
        # Insert two orders directly with explicit timestamps for deterministic ordering
        order1_id = str(uuid.uuid4())
        order2_id = str(uuid.uuid4())

        conn.execute(
            """INSERT INTO orders (id, session_id, status, total_cents,
                                  customer_email, created_at, updated_at)
               VALUES (?, ?, 'pending', 2500, 'a@a.com',
                       '2024-01-01 10:00:00', '2024-01-01 10:00:00')""",
            (order1_id, session_a),
        )
        conn.execute(
            """INSERT INTO orders (id, session_id, status, total_cents,
                                  customer_email, created_at, updated_at)
               VALUES (?, ?, 'pending', 3500, 'a@a.com',
                       '2024-01-02 10:00:00', '2024-01-02 10:00:00')""",
            (order2_id, session_a),
        )
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity) "
            "VALUES (?, 'lavender-dream', 'Lavender Dream', 2500, 1)",
            (order1_id,),
        )
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity) "
            "VALUES (?, 'midnight-amber', 'Midnight Amber', 3500, 1)",
            (order2_id,),
        )
        conn.commit()

        result = list_orders(conn=conn, session_id=session_a)
        # Newest first (order2 was created on Jan 2)
        assert result["items"][0]["id"] == order2_id
        assert result["items"][1]["id"] == order1_id


class TestGetOrder:
    """5.2: get_order returns order for owner, raises for non-owner."""

    def test_owner_can_access(self, conn, cart_with_items, delivery):
        session_id = cart_with_items
        order = checkout(
            conn=conn, session_id=session_id, customer_email="t@t.com", delivery=delivery
        )
        conn.commit()

        result = get_order(conn=conn, order_id=order["id"], session_id=session_id)
        assert result["id"] == order["id"]
        assert len(result["items"]) == 2

    def test_non_owner_gets_not_found(self, conn, cart_with_items, session_b, delivery):
        session_id = cart_with_items
        order = checkout(
            conn=conn, session_id=session_id, customer_email="t@t.com", delivery=delivery
        )
        conn.commit()

        with pytest.raises(OrderNotFoundError):
            get_order(conn=conn, order_id=order["id"], session_id=session_b)


class TestGetOrderAuthenticated:
    """5.3: get_order with user_id finds orders from any session."""

    def test_user_id_access_cross_session(self, conn, session_a, session_b, products, delivery):
        user_id = "user-456"
        conn.execute(
            "INSERT INTO users (id, google_id, email) VALUES (?, ?, ?)",
            (user_id, "g-456", "user456@example.com"),
        )
        conn.commit()

        # Create order under session_a with user_id
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "lavender-dream", 1),
        )
        conn.commit()
        order = checkout(
            conn=conn,
            session_id=session_a,
            customer_email="t@t.com",
            user_id=user_id,
            delivery=delivery,
        )
        conn.commit()

        # Access from session_b with same user_id
        result = get_order(conn=conn, order_id=order["id"], session_id=session_b, user_id=user_id)
        assert result["id"] == order["id"]


class TestListOrdersPagination:
    """5.4: Pagination edge cases."""

    def test_page_beyond_last_returns_empty(self, conn, cart_with_items, delivery):
        checkout(conn=conn, session_id=cart_with_items, customer_email="t@t.com", delivery=delivery)
        conn.commit()

        result = list_orders(conn=conn, session_id=cart_with_items, page=99)
        assert result["items"] == []
        assert result["total"] == 1

    def test_limit_zero_raises(self, conn, session_a):
        with pytest.raises(ValueError, match="limit must be at least 1"):
            list_orders(conn=conn, session_id=session_a, limit=0)

    def test_negative_limit_raises(self, conn, session_a):
        with pytest.raises(ValueError, match="limit must be at least 1"):
            list_orders(conn=conn, session_id=session_a, limit=-1)


# ===========================================================================
# 6. Tests — State Machine & Admin
# ===========================================================================


def _create_order_with_status(conn, session_id, status="pending", products_in_order=None):
    """Helper: insert an order directly with a given status."""
    order_id = str(uuid.uuid4())
    past = (datetime.now(UTC) - timedelta(hours=1)).strftime(_DT_FMT)

    if products_in_order is None:
        products_in_order = [("lavender-dream", "Lavender Dream", 2500, 2)]

    total = sum(p * q for _, _, p, q in products_in_order)

    conn.execute(
        """INSERT INTO orders (id, session_id, status, total_cents, customer_email,
                              created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (order_id, session_id, status, total, "test@test.com", past, past),
    )

    for pid, pname, price, qty in products_in_order:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity) "
            "VALUES (?, ?, ?, ?, ?)",
            (order_id, pid, pname, price, qty),
        )

    conn.commit()
    return order_id


class TestValidTransitions:
    """6.1: All valid state transitions succeed and updated_at is refreshed."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            ("pending", "confirmed"),
            ("pending", "cancelled"),
            ("confirmed", "shipped"),
            ("confirmed", "cancelled"),
            ("shipped", "delivered"),
            ("shipped", "return_in_transit"),
            ("delivered", "return_in_transit"),
            ("return_in_transit", "returned"),
        ],
    )
    def test_valid_transition(self, conn, session_a, products, from_status, to_status):
        order_id = _create_order_with_status(conn, session_a, from_status)

        # Get original updated_at
        original = conn.execute(
            "SELECT updated_at FROM orders WHERE id = ?", (order_id,)
        ).fetchone()[0]

        result = update_status(
            conn=conn,
            order_id=order_id,
            new_status=to_status,
            # Tracking is required on the ship transition (email-notifications).
            tracking_number="1234567" if to_status == "shipped" else None,
            tracking_carrier="speedy" if to_status == "shipped" else None,
        )
        conn.commit()

        assert result["status"] == to_status

        # updated_at refreshed (trigger fires on UPDATE)
        new_updated = conn.execute(
            "SELECT updated_at FROM orders WHERE id = ?", (order_id,)
        ).fetchone()[0]
        assert new_updated != original


class TestInvalidTransitions:
    """6.2: All invalid transitions raise InvalidStateTransitionError."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            ("pending", "shipped"),
            ("pending", "delivered"),
            ("pending", "return_in_transit"),
            ("pending", "returned"),
            ("confirmed", "pending"),
            ("confirmed", "delivered"),
            ("confirmed", "return_in_transit"),
            ("confirmed", "returned"),
            ("shipped", "pending"),
            ("shipped", "confirmed"),
            ("shipped", "cancelled"),
            ("shipped", "returned"),
            ("delivered", "pending"),
            ("delivered", "confirmed"),
            ("delivered", "shipped"),
            ("delivered", "cancelled"),
            ("delivered", "returned"),
            ("returned", "pending"),
            ("returned", "confirmed"),
            ("returned", "shipped"),
            ("returned", "delivered"),
            ("returned", "return_in_transit"),
            ("returned", "cancelled"),
            ("cancelled", "pending"),
            ("cancelled", "confirmed"),
            ("cancelled", "shipped"),
            ("cancelled", "delivered"),
            ("cancelled", "return_in_transit"),
            ("cancelled", "returned"),
        ],
    )
    def test_invalid_transition(self, conn, session_a, products, from_status, to_status):
        order_id = _create_order_with_status(conn, session_a, from_status)

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            update_status(conn=conn, order_id=order_id, new_status=to_status)

        assert exc_info.value.current_status == from_status
        assert exc_info.value.requested_status == to_status


class TestCancellationRestoresStock:
    """6.3, 6.4, 6.5: Cancellation restores stock."""

    def test_cancel_from_pending_restores_stock(self, conn, session_a, products):
        order_id = _create_order_with_status(
            conn,
            session_a,
            "pending",
            products_in_order=[("lavender-dream", "Lavender Dream", 2500, 3)],
        )

        # Decrement stock to simulate checkout (10 - 3 = 7)
        conn.execute("UPDATE products SET stock = 7 WHERE id = 'lavender-dream'")
        conn.commit()

        update_status(conn=conn, order_id=order_id, new_status="cancelled")
        conn.commit()

        stock = conn.execute("SELECT stock FROM products WHERE id = 'lavender-dream'").fetchone()[0]
        assert stock == 10  # 7 + 3 restored

    def test_cancel_with_deactivated_product_restores_stock(self, conn, session_a, products):
        order_id = _create_order_with_status(
            conn,
            session_a,
            "pending",
            products_in_order=[("lavender-dream", "Lavender Dream", 2500, 2)],
        )
        conn.execute("UPDATE products SET stock = 8 WHERE id = 'lavender-dream'")
        conn.execute("UPDATE products SET is_active = 0 WHERE id = 'lavender-dream'")
        conn.commit()

        update_status(conn=conn, order_id=order_id, new_status="cancelled")
        conn.commit()

        stock = conn.execute("SELECT stock FROM products WHERE id = 'lavender-dream'").fetchone()[0]
        assert stock == 10  # 8 + 2

    def test_cancel_from_confirmed_restores_stock(self, conn, session_a, products):
        order_id = _create_order_with_status(
            conn,
            session_a,
            "confirmed",
            products_in_order=[("midnight-amber", "Midnight Amber", 3500, 2)],
        )
        conn.execute("UPDATE products SET stock = 3 WHERE id = 'midnight-amber'")
        conn.commit()

        update_status(conn=conn, order_id=order_id, new_status="cancelled")
        conn.commit()

        stock = conn.execute("SELECT stock FROM products WHERE id = 'midnight-amber'").fetchone()[0]
        assert stock == 5  # 3 + 2


class TestReturnTransitionsDoNotRestoreStock:
    """Post-shipment return statuses are physical workflow, not inventory decisions."""

    def test_shipped_to_return_in_transit_keeps_stock_unchanged(
        self, conn, session_a, products
    ):
        order_id = _create_order_with_status(
            conn,
            session_a,
            "shipped",
            products_in_order=[("lavender-dream", "Lavender Dream", 2500, 2)],
        )
        conn.execute("UPDATE products SET stock = 8 WHERE id = 'lavender-dream'")
        conn.commit()

        result = update_status(conn=conn, order_id=order_id, new_status="return_in_transit")
        conn.commit()

        stock = conn.execute("SELECT stock FROM products WHERE id = 'lavender-dream'").fetchone()[0]
        assert result["status"] == "return_in_transit"
        assert stock == 8

    def test_return_in_transit_to_returned_keeps_stock_unchanged(
        self, conn, session_a, products
    ):
        order_id = _create_order_with_status(
            conn,
            session_a,
            "return_in_transit",
            products_in_order=[("midnight-amber", "Midnight Amber", 3500, 2)],
        )
        conn.execute("UPDATE products SET stock = 3 WHERE id = 'midnight-amber'")
        conn.commit()

        result = update_status(conn=conn, order_id=order_id, new_status="returned")
        conn.commit()

        stock = conn.execute("SELECT stock FROM products WHERE id = 'midnight-amber'").fetchone()[0]
        assert result["status"] == "returned"
        assert stock == 3

    def test_payment_review_order_cannot_ship(self, conn, session_a, products):
        order_id = _create_order_with_status(conn, session_a, "confirmed")
        conn.execute(
            "UPDATE orders SET payment_method = 'card', payment_status = 'review_required' "
            "WHERE id = ?",
            (order_id,),
        )
        conn.commit()

        with pytest.raises(PaymentReviewRequiredError):
            update_status(
                conn=conn,
                order_id=order_id,
                new_status="shipped",
                tracking_number="1234567",
                tracking_carrier="speedy",
            )


class TestDoubleCancellation:
    """6.6: Cancel already-cancelled order raises and stock is NOT double-incremented."""

    def test_double_cancel_prevented(self, conn, session_a, products):
        order_id = _create_order_with_status(
            conn,
            session_a,
            "pending",
            products_in_order=[("lavender-dream", "Lavender Dream", 2500, 2)],
        )
        conn.execute("UPDATE products SET stock = 8 WHERE id = 'lavender-dream'")
        conn.commit()

        # First cancel
        update_status(conn=conn, order_id=order_id, new_status="cancelled")
        conn.commit()

        stock_after_first = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        assert stock_after_first == 10

        # Second cancel attempt
        with pytest.raises(InvalidStateTransitionError):
            update_status(conn=conn, order_id=order_id, new_status="cancelled")

        # Stock not double-incremented
        stock_after_attempt = conn.execute(
            "SELECT stock FROM products WHERE id = 'lavender-dream'"
        ).fetchone()[0]
        assert stock_after_attempt == 10


class TestCheckoutSetsUserId:
    """6.7: Checkout from authenticated session sets user_id on order."""

    def test_user_id_set_on_checkout(self, conn, session_a, products, delivery):
        user_id = "user-789"
        conn.execute(
            "INSERT INTO users (id, google_id, email) VALUES (?, ?, ?)",
            (user_id, "g-789", "user789@example.com"),
        )
        conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user_id, session_a))
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "lavender-dream", 1),
        )
        conn.commit()

        order = checkout(
            conn=conn,
            session_id=session_a,
            customer_email="t@t.com",
            user_id=user_id,
            delivery=delivery,
        )
        conn.commit()

        assert order["user_id"] == user_id

        # New session with same user_id can list the order
        session_new = str(uuid.uuid4())
        now = datetime.now(UTC)
        conn.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (
                session_new,
                user_id,
                now.strftime(_DT_FMT),
                (now + timedelta(days=30)).strftime(_DT_FMT),
            ),
        )
        conn.commit()

        result = list_orders(conn=conn, session_id=session_new, user_id=user_id)
        assert result["total"] == 1
        assert result["items"][0]["id"] == order["id"]


class TestUpdateStatusLog:
    """6.8: update_status emits structured log with order_id, old_status, new_status."""

    def test_status_log_emitted(self, conn, session_a, products):
        import structlog.testing

        order_id = _create_order_with_status(conn, session_a, "pending")

        with structlog.testing.capture_logs() as cap_logs:
            update_status(conn=conn, order_id=order_id, new_status="confirmed")
            conn.commit()

        log_entry = next((e for e in cap_logs if e.get("event") == "Order status updated"), None)
        assert log_entry is not None, f"Expected log entry not found in {cap_logs}"
        assert log_entry["order_id"] == order_id
        assert log_entry["old_status"] == "pending"
        assert log_entry["new_status"] == "confirmed"


class TestShippingTracking:
    """3.6 / 2.3: tracking persistence, required-on-ship, and URL auto-generation."""

    def _confirm(self, conn, session_id):
        order_id = _create_order_with_status(conn, session_id, "confirmed")
        return order_id

    def test_ship_with_tracking_persists(self, conn, session_a, products):
        order_id = self._confirm(conn, session_a)
        result = update_status(
            conn=conn,
            order_id=order_id,
            new_status="shipped",
            tracking_number="1234567",
            tracking_carrier="speedy",
        )
        conn.commit()
        assert result["status"] == "shipped"
        assert result["tracking_number"] == "1234567"
        assert result["tracking_carrier"] == "speedy"
        # URL auto-generated from the known carrier pattern.
        assert result["tracking_url"] == (
            "https://www.speedy.bg/en/track-shipment?shipmentNumber=1234567"
        )

    def test_ship_without_tracking_number_rejected(self, conn, session_a, products):
        order_id = self._confirm(conn, session_a)
        with pytest.raises(TrackingRequiredError) as exc:
            update_status(
                conn=conn, order_id=order_id, new_status="shipped", tracking_carrier="speedy"
            )
        assert "tracking_number" in exc.value.missing

    def test_ship_without_carrier_rejected(self, conn, session_a, products):
        order_id = self._confirm(conn, session_a)
        with pytest.raises(TrackingRequiredError) as exc:
            update_status(conn=conn, order_id=order_id, new_status="shipped", tracking_number="123")
        assert "tracking_carrier" in exc.value.missing

    def test_custom_url_not_overwritten(self, conn, session_a, products):
        order_id = self._confirm(conn, session_a)
        result = update_status(
            conn=conn,
            order_id=order_id,
            new_status="shipped",
            tracking_number="999",
            tracking_carrier="other",
            tracking_url="https://custom.example/track/999",
        )
        conn.commit()
        assert result["tracking_url"] == "https://custom.example/track/999"

    def test_unknown_carrier_no_autogen(self, conn, session_a, products):
        order_id = self._confirm(conn, session_a)
        result = update_status(
            conn=conn,
            order_id=order_id,
            new_status="shipped",
            tracking_number="999",
            tracking_carrier="other",
        )
        conn.commit()
        assert result["tracking_url"] is None

    @pytest.mark.parametrize(
        "carrier,number,expected",
        [
            ("speedy", "1234567", "https://www.speedy.bg/en/track-shipment?shipmentNumber=1234567"),
            ("econt", "1234567", "https://www.econt.com/services/track-shipment/1234567"),
            ("dhl", "1234567", "https://www.dhl.com/en/express/tracking.html?AWB=1234567"),
            ("fedex", "1234567", "https://www.fedex.com/fedextrack/?trknbr=1234567"),
            ("other", "1234567", None),
            (None, "1234567", None),
            ("speedy", None, None),
        ],
    )
    def test_tracking_url_for(self, carrier, number, expected):
        from app.constants import tracking_url_for

        assert tracking_url_for(carrier, number) == expected


class TestSpeedyWaybillAutomation:
    """Speedy-specific ship transition creates and persists a waybill."""

    def _speedy_order(self, conn, session_id):
        order_id = _create_order_with_status(conn, session_id, "confirmed")
        conn.execute(
            """
            UPDATE orders
            SET delivery_method = 'door', delivery_courier = 'speedy',
                customer_name = 'Mira', delivery_details = ?
            WHERE id = ?
            """,
            (
                json.dumps(
                    {
                        "courier": "speedy",
                        "city": "София",
                        "postal_code": "1000",
                        "street": "Витоша",
                        "building": "5",
                        "phone": "+359888123456",
                    },
                    ensure_ascii=False,
                ),
                order_id,
            ),
        )
        conn.commit()
        return order_id

    def test_sync_ship_speedy_without_tracking_requires_tracking(
        self, conn, session_a, monkeypatch
    ):
        from app.services import speedy_client

        order_id = self._speedy_order(conn, session_a)

        def fail_if_called(**_kwargs):
            raise AssertionError("sync status update must not call Speedy")

        monkeypatch.setattr(speedy_client, "create_shipment_sync", fail_if_called)

        with pytest.raises(TrackingRequiredError) as exc_info:
            update_status(conn=conn, order_id=order_id, new_status="shipped")

        assert "tracking_number" in exc_info.value.missing

    @pytest.mark.asyncio
    async def test_ship_speedy_order_creates_waybill_and_tracking(
        self, conn, session_a, monkeypatch
    ):
        from app.services import speedy_client

        order_id = self._speedy_order(conn, session_a)
        captured: dict = {}

        async def fake_create_shipment(**kwargs):
            captured.update(kwargs)
            return "63689182611"

        monkeypatch.setattr(speedy_client, "create_shipment", fake_create_shipment)

        result = await update_status_async(conn=conn, order_id=order_id, new_status="shipped")
        conn.commit()

        assert result["status"] == "shipped"
        assert result["tracking_number"] == "63689182611"
        assert result["tracking_carrier"] == "speedy"
        assert result["tracking_url"] == (
            "https://www.speedy.bg/en/track-shipment?shipmentNumber=63689182611"
        )
        assert captured["recipient_name"] == "Mira"
        assert captured["recipient_phone"] == "+359888123456"
        assert captured["recipient_city"] == "София"
        assert captured["recipient_postcode"] == "1000"
        assert captured["recipient_street"] == "Витоша"
        assert captured["recipient_building"] == "5"
        assert captured["weight_grams"] == 600
        assert captured["cod_amount_cents"] == result["total_cents"]

    @pytest.mark.asyncio
    async def test_speedy_waybill_failure_leaves_order_confirmed(
        self, conn, session_a, monkeypatch
    ):
        from app.services import speedy_client

        order_id = self._speedy_order(conn, session_a)

        async def fail_create_shipment(**kwargs):
            raise speedy_client.ShipmentCreationError("phone required", context="recipient.phone")

        monkeypatch.setattr(speedy_client, "create_shipment", fail_create_shipment)

        with pytest.raises(speedy_client.ShipmentCreationError) as exc_info:
            await update_status_async(conn=conn, order_id=order_id, new_status="shipped")

        assert exc_info.value.context == "recipient.phone"
        row = conn.execute(
            "SELECT status, tracking_number FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        assert row["status"] == "confirmed"
        assert row["tracking_number"] is None


class TestLocaleSnapshot:
    """2.6: order created with locale 'bg' persists orders.locale = 'bg'."""

    def test_checkout_snapshots_locale(self, conn, session_a, cart_with_items, delivery):
        order = checkout(
            conn=conn,
            session_id=session_a,
            customer_email="buyer@example.com",
            delivery=delivery,
            locale="bg",
        )
        assert order["locale"] == "bg"
        row = conn.execute("SELECT locale FROM orders WHERE id = ?", (order["id"],)).fetchone()
        assert row["locale"] == "bg"

    def test_checkout_defaults_locale_en(self, conn, session_a, cart_with_items, delivery):
        order = checkout(
            conn=conn,
            session_id=session_a,
            customer_email="buyer@example.com",
            delivery=delivery,
        )
        assert order["locale"] == "en"


class TestBackfillUserId:
    """6.9: Backfill user_id on login for existing orders."""

    def test_backfill_user_id_on_orders(self, conn, session_a, products, delivery):
        # Create order without user_id
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (session_a, "lavender-dream", 1),
        )
        conn.commit()
        order = checkout(
            conn=conn, session_id=session_a, customer_email="t@t.com", delivery=delivery
        )
        conn.commit()

        assert order["user_id"] is None

        # Simulate login backfill
        user_id = "user-backfill"
        conn.execute(
            "INSERT INTO users (id, google_id, email) VALUES (?, ?, ?)",
            (user_id, "g-bf", "bf@example.com"),
        )
        conn.execute(
            "UPDATE orders SET user_id = ? WHERE session_id = ? AND user_id IS NULL",
            (user_id, session_a),
        )
        conn.commit()

        # Verify backfill
        row = conn.execute("SELECT user_id FROM orders WHERE id = ?", (order["id"],)).fetchone()
        assert row[0] == user_id
