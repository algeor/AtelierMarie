"""Integration tests for database schema constraints (CHECK, FK, triggers)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.database import IntegrityError, get_db


@pytest.fixture(autouse=True)
def _pool(app):
    """Ensure the psycopg pool is initialized (app fixture opens it)."""
    return app


class TestProductConstraints:
    def test_negative_stock_rejected(self):
        """CHECK (stock >= 0) rejects negative stock."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (%s, %s, %s, %s)",
                ("test-candle", "Test", 1000, -1),
            )

    def test_zero_price_rejected(self):
        """CHECK (price_cents > 0) rejects zero price."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (%s, %s, %s, %s)",
                ("test-candle", "Test", 0, 10),
            )

    def test_negative_price_rejected(self):
        """CHECK (price_cents > 0) rejects negative price."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (%s, %s, %s, %s)",
                ("test-candle", "Test", -500, 10),
            )

    def test_zero_weight_rejected(self):
        """CHECK (weight_grams > 0) rejects zero weight."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, weight_grams) "
                "VALUES (%s, %s, %s, %s)",
                ("test-candle", "Test", 1000, 0),
            )

    def test_negative_weight_rejected(self):
        """CHECK (weight_grams > 0) rejects negative weight."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, weight_grams) "
                "VALUES (%s, %s, %s, %s)",
                ("test-candle", "Test", 1000, -5),
            )

    def test_valid_product_accepted(self):
        """A valid product row is accepted by all constraints."""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (%s, %s, %s, %s)",
                ("test-candle", "Test Candle", 1500, 5),
            )
            row = conn.execute("SELECT * FROM products WHERE id = %s", ("test-candle",)).fetchone()
        assert row is not None
        assert row["price_cents"] == 1500
        assert row["stock"] == 5


class TestCartItemConstraints:
    @pytest.fixture(autouse=True)
    def _seed(self):
        """Insert prerequisite session and product."""
        future = datetime.now(UTC) + timedelta(days=1)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO sessions (id, expires_at) VALUES (%s, %s)", ("sess-1", future)
            )
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (%s, %s, %s, %s)",
                ("prod-1", "Product", 1000, 10),
            )

    def test_zero_quantity_rejected(self):
        """CHECK (quantity >= 1) rejects zero quantity."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
                ("sess-1", "prod-1", 0),
            )

    def test_quantity_over_max_rejected(self):
        """CHECK (quantity <= 10) rejects quantity exceeding limit."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
                ("sess-1", "prod-1", 11),
            )

    def test_valid_quantity_accepted(self):
        """A valid cart item row is accepted."""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
                ("sess-1", "prod-1", 3),
            )

    def test_cascade_delete_on_session_removal(self):
        """Cart items are deleted when their session is deleted (ON DELETE CASCADE)."""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
                ("sess-1", "prod-1", 2),
            )
            # Delete the session
            conn.execute("DELETE FROM sessions WHERE id = %s", ("sess-1",))
            # Cart items should be gone
            rows = conn.execute(
                "SELECT * FROM cart_items WHERE session_id = %s", ("sess-1",)
            ).fetchall()
        assert len(rows) == 0


class TestOrderConstraints:
    def test_invalid_status_rejected(self):
        """CHECK on status rejects invalid values."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO orders (id, session_id, total_cents, customer_email, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                ("ord-1", "sess-1", 1000, "test@example.com", "bogus"),
            )

    def test_valid_statuses_accepted(self):
        """All valid order statuses are accepted."""
        with get_db() as conn:
            for i, status in enumerate(
                ("pending", "confirmed", "shipped", "delivered", "cancelled")
            ):
                conn.execute(
                    "INSERT INTO orders (id, session_id, total_cents, customer_email, status) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (f"ord-{i}", "sess-1", 1000, "test@example.com", status),
                )


class TestOrderItemConstraints:
    @pytest.fixture(autouse=True)
    def _seed(self):
        """Insert a prerequisite order."""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO orders (id, session_id, total_cents, customer_email) "
                "VALUES (%s, %s, %s, %s)",
                ("ord-1", "sess-1", 3000, "test@example.com"),
            )

    def test_zero_price_rejected(self):
        """CHECK (price_cents > 0) rejects zero in order items."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO order_items"
                " (order_id, product_id, product_name, price_cents, quantity)"
                " VALUES (%s, %s, %s, %s, %s)",
                ("ord-1", "prod-1", "Test", 0, 1),
            )

    def test_zero_quantity_rejected(self):
        """CHECK (quantity > 0) rejects zero quantity in order items."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO order_items"
                " (order_id, product_id, product_name, price_cents, quantity)"
                " VALUES (%s, %s, %s, %s, %s)",
                ("ord-1", "prod-1", "Test", 1000, 0),
            )

    def test_quantity_over_max_rejected(self):
        """CHECK (quantity <= 99) rejects quantity exceeding limit in order items."""
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO order_items"
                " (order_id, product_id, product_name, price_cents, quantity)"
                " VALUES (%s, %s, %s, %s, %s)",
                ("ord-1", "prod-1", "Test", 1000, 100),
            )

    def test_valid_order_item_accepted(self):
        """A valid order item is accepted."""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO order_items "
                "(order_id, product_id, product_name, price_cents, quantity, allocated_quantity, backordered_quantity) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ("ord-1", "prod-1", "Lavender Dreams", 1500, 2, 2, 0),
            )


class TestUpdatedAtTriggers:
    def test_products_updated_at_auto_updates(self):
        """Updating a product row auto-updates its updated_at timestamp."""
        old = datetime(2020, 1, 1, tzinfo=UTC)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, updated_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                ("test-candle", "Test", 1000, 5, old),
            )
            # Update the product
            conn.execute(
                "UPDATE products SET name_en = %s WHERE id = %s",
                ("Updated", "test-candle"),
            )
            row = conn.execute(
                "SELECT updated_at FROM products WHERE id = %s", ("test-candle",)
            ).fetchone()
        stored = row["updated_at"]
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=UTC)
        # updated_at should no longer be the old value
        assert stored != old

    def test_orders_updated_at_auto_updates(self):
        """Updating an order row auto-updates its updated_at timestamp."""
        old = datetime(2020, 1, 1, tzinfo=UTC)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO orders (id, session_id, total_cents, customer_email, updated_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                ("ord-1", "sess-1", 3000, "test@example.com", old),
            )
            # Update the order status
            conn.execute("UPDATE orders SET status = %s WHERE id = %s", ("confirmed", "ord-1"))
            row = conn.execute("SELECT updated_at FROM orders WHERE id = %s", ("ord-1",)).fetchone()
        stored = row["updated_at"]
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=UTC)
        assert stored != old
