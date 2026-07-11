"""Tests for database layer — schema constraints and utility functions."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.database import cleanup_expired_sessions, init_db

# SQLite-compatible datetime format (matches middleware's _SQLITE_DT_FMT)
_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def db_conn(db_path: str) -> sqlite3.Connection:
    """Yield a raw connection to the test DB."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


class TestCleanupExpiredSessions:
    """Verify cleanup_expired_sessions() deletes only expired rows."""

    @pytest.fixture(autouse=True)
    def _clear_all_sessions(self, db_conn):
        """Remove all pre-existing sessions so tests start from a clean slate."""
        db_conn.execute("DELETE FROM sessions")
        db_conn.commit()
        yield

    def test_removes_expired_sessions(self, db_conn: sqlite3.Connection):
        expired_at = (datetime.now(UTC) - timedelta(days=1)).strftime(_DT_FMT)
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("expired-1", expired_at),
        )
        db_conn.commit()

        count = cleanup_expired_sessions()

        assert count == 1
        row = db_conn.execute("SELECT id FROM sessions WHERE id = ?", ("expired-1",)).fetchone()
        assert row is None

    def test_keeps_active_sessions(self, db_conn: sqlite3.Connection):
        active_at = (datetime.now(UTC) + timedelta(days=1)).strftime(_DT_FMT)
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("active-1", active_at),
        )
        db_conn.commit()

        count = cleanup_expired_sessions()

        assert count == 0
        row = db_conn.execute("SELECT id FROM sessions WHERE id = ?", ("active-1",)).fetchone()
        assert row is not None

    def test_mixed_expired_and_active(self, db_conn: sqlite3.Connection):
        expired_at = (datetime.now(UTC) - timedelta(hours=1)).strftime(_DT_FMT)
        active_at = (datetime.now(UTC) + timedelta(hours=1)).strftime(_DT_FMT)
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("expired-a", expired_at),
        )
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("active-a", active_at),
        )
        db_conn.commit()

        count = cleanup_expired_sessions()

        assert count == 1
        rows = db_conn.execute("SELECT id FROM sessions ORDER BY id").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "active-a"

    def test_returns_zero_when_no_sessions(self, db_conn: sqlite3.Connection):
        count = cleanup_expired_sessions()
        assert count == 0


class TestDatabaseConstraints:
    """Verify CHECK constraints enforce data integrity at the DB level."""

    def test_product_price_zero_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock)"
                " VALUES ('test', 'Test', 0, 5)"
            )

    def test_product_price_negative_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('test', 'Test', -100, 5)"
            )

    def test_product_negative_stock_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('test', 'Test', 1000, -1)"
            )

    def test_product_zero_stock_allowed(self, db_conn: sqlite3.Connection):
        db_conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock)"
            " VALUES ('test', 'Test', 1000, 0)"
        )
        db_conn.commit()
        row = db_conn.execute("SELECT stock FROM products WHERE id = 'test'").fetchone()
        assert row[0] == 0

    def test_order_invalid_status_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                "VALUES ('o1', 's1', 'invalid_status', 100, 'test@example.com')"
            )

    def test_order_valid_statuses_accepted(self, db_conn: sqlite3.Connection):
        for i, status in enumerate(("pending", "confirmed", "shipped", "delivered", "cancelled")):
            db_conn.execute(
                "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                "VALUES (?, 's1', ?, 100, 'test@example.com')",
                (f"order-{i}", status),
            )
        db_conn.commit()
        rows = db_conn.execute("SELECT COUNT(*) FROM orders").fetchone()
        assert rows[0] == 5

    def test_cart_items_cascade_on_session_delete(self, db_conn: sqlite3.Connection):
        """Deleting a session cascades to its cart items."""
        # Insert a session and a product
        expires = (datetime.now(UTC) + timedelta(days=1)).strftime(_DT_FMT)
        db_conn.execute("INSERT INTO sessions (id, expires_at) VALUES ('s1', ?)", (expires,))
        db_conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock) "
            "VALUES ('prod-1', 'Test Product', 1000, 10)"
        )
        db_conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES ('s1', 'prod-1', 2)"
        )
        db_conn.commit()

        # Delete the session
        db_conn.execute("DELETE FROM sessions WHERE id = 's1'")
        db_conn.commit()

        # Cart items should be gone (CASCADE)
        row = db_conn.execute("SELECT COUNT(*) FROM cart_items WHERE session_id = 's1'").fetchone()
        assert row[0] == 0
