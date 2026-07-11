"""Integration tests for database schema constraints (CHECK, FK, triggers)."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def conn(db_path: str, app) -> sqlite3.Connection:
    """Return a raw connection to the test DB for constraint testing."""
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


class TestProductConstraints:
    def test_negative_stock_rejected(self, conn: sqlite3.Connection):
        """CHECK (stock >= 0) rejects negative stock."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, ?)",
                ("test-candle", "Test", 1000, -1),
            )

    def test_zero_price_rejected(self, conn: sqlite3.Connection):
        """CHECK (price_cents > 0) rejects zero price."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, ?)",
                ("test-candle", "Test", 0, 10),
            )

    def test_negative_price_rejected(self, conn: sqlite3.Connection):
        """CHECK (price_cents > 0) rejects negative price."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, ?)",
                ("test-candle", "Test", -500, 10),
            )

    def test_valid_product_accepted(self, conn: sqlite3.Connection):
        """A valid product row is accepted by all constraints."""
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, ?)",
            ("test-candle", "Test Candle", 1500, 5),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id = ?", ("test-candle",)).fetchone()
        assert row is not None
        assert row["price_cents"] == 1500
        assert row["stock"] == 5


class TestCartItemConstraints:
    @pytest.fixture(autouse=True)
    def _seed(self, conn: sqlite3.Connection):
        """Insert prerequisite session and product."""
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        conn.execute("INSERT INTO sessions (id, expires_at) VALUES (?, ?)", ("sess-1", future))
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, ?)",
            ("prod-1", "Product", 1000, 10),
        )
        conn.commit()

    def test_zero_quantity_rejected(self, conn: sqlite3.Connection):
        """CHECK (quantity >= 1) rejects zero quantity."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
                ("sess-1", "prod-1", 0),
            )

    def test_quantity_over_max_rejected(self, conn: sqlite3.Connection):
        """CHECK (quantity <= 99) rejects quantity exceeding limit."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
                ("sess-1", "prod-1", 100),
            )

    def test_valid_quantity_accepted(self, conn: sqlite3.Connection):
        """A valid cart item row is accepted."""
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            ("sess-1", "prod-1", 3),
        )
        conn.commit()

    def test_cascade_delete_on_session_removal(self, conn: sqlite3.Connection):
        """Cart items are deleted when their session is deleted (ON DELETE CASCADE)."""
        conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            ("sess-1", "prod-1", 2),
        )
        conn.commit()

        # Delete the session
        conn.execute("DELETE FROM sessions WHERE id = ?", ("sess-1",))
        conn.commit()

        # Cart items should be gone
        rows = conn.execute("SELECT * FROM cart_items WHERE session_id = ?", ("sess-1",)).fetchall()
        assert len(rows) == 0


class TestOrderConstraints:
    def test_invalid_status_rejected(self, conn: sqlite3.Connection):
        """CHECK on status rejects invalid values."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO orders (id, session_id, total_cents, customer_email, status) "
                "VALUES (?, ?, ?, ?, ?)",
                ("ord-1", "sess-1", 1000, "test@example.com", "bogus"),
            )

    def test_valid_statuses_accepted(self, conn: sqlite3.Connection):
        """All valid order statuses are accepted."""
        for i, status in enumerate(("pending", "confirmed", "shipped", "delivered", "cancelled")):
            conn.execute(
                "INSERT INTO orders (id, session_id, total_cents, customer_email, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"ord-{i}", "sess-1", 1000, "test@example.com", status),
            )
        conn.commit()


class TestOrderItemConstraints:
    @pytest.fixture(autouse=True)
    def _seed(self, conn: sqlite3.Connection):
        """Insert a prerequisite order."""
        conn.execute(
            "INSERT INTO orders (id, session_id, total_cents, customer_email) VALUES (?, ?, ?, ?)",
            ("ord-1", "sess-1", 3000, "test@example.com"),
        )
        conn.commit()

    def test_zero_price_rejected(self, conn: sqlite3.Connection):
        """CHECK (price_cents > 0) rejects zero in order items."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO order_items"
                " (order_id, product_id, product_name, price_cents, quantity)"
                " VALUES (?, ?, ?, ?, ?)",
                ("ord-1", "prod-1", "Test", 0, 1),
            )

    def test_zero_quantity_rejected(self, conn: sqlite3.Connection):
        """CHECK (quantity > 0) rejects zero quantity in order items."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO order_items"
                " (order_id, product_id, product_name, price_cents, quantity)"
                " VALUES (?, ?, ?, ?, ?)",
                ("ord-1", "prod-1", "Test", 1000, 0),
            )

    def test_quantity_over_max_rejected(self, conn: sqlite3.Connection):
        """CHECK (quantity <= 99) rejects quantity exceeding limit in order items."""
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO order_items"
                " (order_id, product_id, product_name, price_cents, quantity)"
                " VALUES (?, ?, ?, ?, ?)",
                ("ord-1", "prod-1", "Test", 1000, 100),
            )

    def test_valid_order_item_accepted(self, conn: sqlite3.Connection):
        """A valid order item is accepted."""
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity) "
            "VALUES (?, ?, ?, ?, ?)",
            ("ord-1", "prod-1", "Lavender Dreams", 1500, 2),
        )
        conn.commit()


class TestUpdatedAtTriggers:
    def test_products_updated_at_auto_updates(self, conn: sqlite3.Connection):
        """Updating a product row auto-updates its updated_at timestamp."""
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("test-candle", "Test", 1000, 5, "2020-01-01T00:00:00"),
        )
        conn.commit()

        # Update the product
        conn.execute(
            "UPDATE products SET name_en = ? WHERE id = ?",
            ("Updated", "test-candle"),
        )
        conn.commit()

        row = conn.execute(
            "SELECT updated_at FROM products WHERE id = ?", ("test-candle",)
        ).fetchone()
        # updated_at should no longer be the old value
        assert row["updated_at"] != "2020-01-01T00:00:00"

    def test_orders_updated_at_auto_updates(self, conn: sqlite3.Connection):
        """Updating an order row auto-updates its updated_at timestamp."""
        conn.execute(
            "INSERT INTO orders (id, session_id, total_cents, customer_email, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("ord-1", "sess-1", 3000, "test@example.com", "2020-01-01T00:00:00"),
        )
        conn.commit()

        # Update the order status
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", ("confirmed", "ord-1"))
        conn.commit()

        row = conn.execute("SELECT updated_at FROM orders WHERE id = ?", ("ord-1",)).fetchone()
        assert row["updated_at"] != "2020-01-01T00:00:00"
