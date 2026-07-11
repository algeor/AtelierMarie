"""Tests for cart service layer — business logic without HTTP."""

import sqlite3
import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.services.cart_service import (
    CartFullError,
    CartItemNotFoundError,
    InsufficientStockError,
    ProductNotFoundError,
    QuantityLimitError,
    add_item,
    get_cart,
    remove_item,
    update_quantity,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


# --- Fixtures ---


@pytest.fixture()
def cart_db(db_path: str, app) -> sqlite3.Connection:
    """Return a connection with test products and a session set up."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    # Session
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        ("test-session", now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )

    # Products with varying stock
    products = [
        ("lavender-dream", "Lavender Dream", 2500, 10, 1),
        ("rose-garden", "Rose Garden", 1800, 5, 1),
        ("midnight-musk", "Midnight Musk", 3200, 0, 1),  # Out of stock
        ("winter-pine", "Winter Pine", 2000, 8, 0),  # Inactive
        ("ocean-breeze", "Ocean Breeze", 1500, 20, 1),  # High stock
    ]
    for pid, name, price, stock, active in products:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, "
            "is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (pid, name, price, stock, active),
        )

    conn.commit()
    yield conn
    conn.close()


SESSION_ID = "test-session"


# --- 8.1 Test fixtures created (implicitly by cart_db) ---
# --- 8.2 Test get_cart ---


class TestGetCart:
    """Tests for get_cart service function."""

    def test_empty_cart(self, cart_db: sqlite3.Connection):
        """Empty cart returns zero items and zero totals."""
        cart = get_cart(cart_db, SESSION_ID)
        assert cart.items == []
        assert cart.total_cents == 0
        assert cart.item_count == 0
        assert cart.unavailable_items == []

    def test_cart_with_items_totals(self, cart_db: sqlite3.Connection):
        """Cart with items computes total_cents correctly: price_cents × quantity."""
        cart_db.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (SESSION_ID, "lavender-dream", 2),
        )
        cart_db.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (SESSION_ID, "rose-garden", 3),
        )
        cart_db.commit()

        cart = get_cart(cart_db, SESSION_ID)
        assert len(cart.items) == 2
        # 2500*2 + 1800*3 = 5000 + 5400 = 10400
        assert cart.total_cents == 10400
        assert cart.item_count == 5  # 2 + 3

    def test_inactive_product_in_unavailable(self, cart_db: sqlite3.Connection):
        """Inactive product appears in unavailable_items with product_name."""
        cart_db.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
            (SESSION_ID, "winter-pine", 1),
        )
        cart_db.commit()

        cart = get_cart(cart_db, SESSION_ID)
        assert len(cart.items) == 0
        assert len(cart.unavailable_items) == 1
        assert cart.unavailable_items[0].product_id == "winter-pine"
        assert cart.unavailable_items[0].product_name == "Winter Pine"
        assert cart.unavailable_items[0].reason == "deactivated"


# --- 8.3 Test add_item ---


class TestAddItem:
    """Tests for add_item service function."""

    def test_add_new_item_created_true(self, cart_db: sqlite3.Connection):
        """Adding a new item returns created=True."""
        result = add_item(cart_db, SESSION_ID, "lavender-dream", 2)
        assert result.created is True
        assert len(result.cart.items) == 1
        assert result.cart.items[0].quantity == 2

    def test_add_existing_item_created_false(self, cart_db: sqlite3.Connection):
        """Incrementing existing item returns created=False."""
        add_item(cart_db, SESSION_ID, "lavender-dream", 2)
        result = add_item(cart_db, SESSION_ID, "lavender-dream", 1)
        assert result.created is False
        assert result.cart.items[0].quantity == 3

    def test_add_product_not_found(self, cart_db: sqlite3.Connection):
        """Adding a non-existent product raises ProductNotFoundError."""
        with pytest.raises(ProductNotFoundError):
            add_item(cart_db, SESSION_ID, "nonexistent-product", 1)

    def test_add_inactive_product_not_found(self, cart_db: sqlite3.Connection):
        """Adding an inactive product raises ProductNotFoundError."""
        with pytest.raises(ProductNotFoundError):
            add_item(cart_db, SESSION_ID, "winter-pine", 1)


# --- 8.4 Test add_item stock validation ---


class TestAddItemStock:
    """Tests for stock validation in add_item."""

    def test_sufficient_stock(self, cart_db: sqlite3.Connection):
        """Adding within stock limits succeeds."""
        result = add_item(cart_db, SESSION_ID, "lavender-dream", 5)
        assert result.cart.items[0].quantity == 5

    def test_insufficient_stock_new_add(self, cart_db: sqlite3.Connection):
        """Requesting more than stock raises InsufficientStockError."""
        with pytest.raises(InsufficientStockError) as exc_info:
            add_item(cart_db, SESSION_ID, "rose-garden", 6)  # stock=5
        assert exc_info.value.available == 5
        assert exc_info.value.requested == 6

    def test_insufficient_stock_with_existing_qty(self, cart_db: sqlite3.Connection):
        """Existing qty 3 + add 4 = 7 > stock 5 → fail."""
        add_item(cart_db, SESSION_ID, "rose-garden", 3)
        with pytest.raises(InsufficientStockError) as exc_info:
            add_item(cart_db, SESSION_ID, "rose-garden", 4)
        assert exc_info.value.requested == 7  # 3 + 4
        assert exc_info.value.available == 5


# --- 8.5 Test add_item quantity limits ---


class TestAddItemLimits:
    """Tests for quantity limit enforcement in add_item."""

    def test_per_item_limit_exceeded(self, cart_db: sqlite3.Connection):
        """Existing qty 8 + add 4 = 12 > max 10 → QuantityLimitError."""
        add_item(cart_db, SESSION_ID, "ocean-breeze", 8)  # stock=20, plenty
        with pytest.raises(QuantityLimitError) as exc_info:
            add_item(cart_db, SESSION_ID, "ocean-breeze", 4)
        assert exc_info.value.max_quantity == 10

    def test_cart_full(self, cart_db: sqlite3.Connection):
        """20 distinct items + new → CartFullError."""
        # Add 20 distinct products (need to create them first)
        for i in range(20):
            pid = f"bulk-product-{i:03d}"
            cart_db.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, "
                "is_active, created_at, updated_at) "
                "VALUES (?, ?, 1000, 50, 1, datetime('now'), datetime('now'))",
                (pid, f"Bulk Product {i}"),
            )
        cart_db.commit()

        for i in range(20):
            add_item(cart_db, SESSION_ID, f"bulk-product-{i:03d}", 1)

        # 21st distinct item should fail
        with pytest.raises(CartFullError) as exc_info:
            add_item(cart_db, SESSION_ID, "lavender-dream", 1)
        assert exc_info.value.max_items == 20

    def test_existing_item_when_cart_full(self, cart_db: sqlite3.Connection):
        """Adding more of an existing item when cart is full succeeds."""
        for i in range(19):
            pid = f"fill-product-{i:03d}"
            cart_db.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, "
                "is_active, created_at, updated_at) "
                "VALUES (?, ?, 1000, 50, 1, datetime('now'), datetime('now'))",
                (pid, f"Fill Product {i}"),
            )
        cart_db.commit()

        # Fill cart to 20 distinct items (19 fill + ocean-breeze)
        add_item(cart_db, SESSION_ID, "ocean-breeze", 1)
        for i in range(19):
            add_item(cart_db, SESSION_ID, f"fill-product-{i:03d}", 1)

        # Adding more of existing item should succeed
        result = add_item(cart_db, SESSION_ID, "ocean-breeze", 1)
        assert result.created is False


# --- 8.6 Test update_quantity ---


class TestUpdateQuantity:
    """Tests for update_quantity service function."""

    def test_valid_update(self, cart_db: sqlite3.Connection):
        """Valid update changes quantity."""
        add_item(cart_db, SESSION_ID, "lavender-dream", 2)
        cart = update_quantity(cart_db, SESSION_ID, "lavender-dream", 5)
        assert cart.items[0].quantity == 5

    def test_update_to_zero_removes(self, cart_db: sqlite3.Connection):
        """Update to zero removes the item."""
        add_item(cart_db, SESSION_ID, "lavender-dream", 3)
        cart = update_quantity(cart_db, SESSION_ID, "lavender-dream", 0)
        assert len(cart.items) == 0

    def test_update_exceeds_stock(self, cart_db: sqlite3.Connection):
        """Update to quantity exceeding stock raises InsufficientStockError."""
        add_item(cart_db, SESSION_ID, "rose-garden", 2)
        with pytest.raises(InsufficientStockError) as exc_info:
            update_quantity(cart_db, SESSION_ID, "rose-garden", 8)  # stock=5
        assert exc_info.value.available == 5
        assert exc_info.value.requested == 8

    def test_update_exceeds_per_item_limit(self, cart_db: sqlite3.Connection):
        """Update to quantity exceeding per-item limit raises QuantityLimitError."""
        add_item(cart_db, SESSION_ID, "ocean-breeze", 5)
        with pytest.raises(QuantityLimitError) as exc_info:
            update_quantity(cart_db, SESSION_ID, "ocean-breeze", 11)
        assert exc_info.value.max_quantity == 10

    def test_update_item_not_in_cart(self, cart_db: sqlite3.Connection):
        """Updating non-existent cart item raises CartItemNotFoundError."""
        with pytest.raises(CartItemNotFoundError):
            update_quantity(cart_db, SESSION_ID, "lavender-dream", 5)


# --- 8.7 Test remove_item ---


class TestRemoveItem:
    """Tests for remove_item service function."""

    def test_remove_existing(self, cart_db: sqlite3.Connection):
        """Removing existing item succeeds."""
        add_item(cart_db, SESSION_ID, "lavender-dream", 2)
        cart = remove_item(cart_db, SESSION_ID, "lavender-dream")
        assert len(cart.items) == 0

    def test_remove_nonexistent_raises(self, cart_db: sqlite3.Connection):
        """Removing non-existent item raises CartItemNotFoundError."""
        with pytest.raises(CartItemNotFoundError):
            remove_item(cart_db, SESSION_ID, "lavender-dream")


# --- 8.8 Test total_cents with multiple items (different scenario from TestGetCart) ---


def test_total_cents_excludes_unavailable_items(cart_db: sqlite3.Connection):
    """Unavailable (inactive) items are NOT counted in total_cents."""
    add_item(cart_db, SESSION_ID, "lavender-dream", 2)  # 2500 × 2 = 5000
    add_item(cart_db, SESSION_ID, "rose-garden", 3)  # 1800 × 3 = 5400

    # Deactivate one product
    cart_db.execute("UPDATE products SET is_active = 0 WHERE id = 'rose-garden'")
    cart_db.commit()

    cart = get_cart(cart_db, SESSION_ID)
    # Only lavender-dream (active) counts toward total
    assert cart.total_cents == 5000
    assert cart.item_count == 2
    assert len(cart.unavailable_items) == 1


# --- 8.9 Test concurrent stock depletion ---


def test_concurrent_stock_depletion(db_path: str, app):
    """Two threads competing for stock=1 — BEGIN IMMEDIATE serializes writes.

    Stock validation in add_item is advisory (per design): it reads products.stock
    but never decrements it. The actual stock decrement happens at checkout.
    With stock=1 and two sessions each requesting qty=1:
    - The first thread to acquire the IMMEDIATE lock succeeds (stock 1 >= 1 ✓)
    - The second thread sees the same stock value (not yet decremented) and also succeeds
    This is expected — BEGIN IMMEDIATE prevents *concurrent* reads from seeing
    inconsistent cart_items state, but does NOT prevent over-allocation of stock
    across sessions (that's resolved at checkout time).
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    now = datetime.now(UTC)

    # Create two sessions and a product with stock=1
    for sid in ("session-a", "session-b"):
        conn.execute(
            "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
            (sid, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
        )
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at) "
        "VALUES ('race-product', 'Race Product', 1000, 1, 1, datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    results = {"a": None, "b": None}
    errors = {"a": None, "b": None}

    def worker(session_id: str, key: str):
        c = sqlite3.connect(db_path)
        c.execute("PRAGMA foreign_keys=ON")
        c.row_factory = sqlite3.Row
        try:
            result = add_item(c, session_id, "race-product", 1)
            results[key] = result
        except InsufficientStockError as e:
            errors[key] = e
        finally:
            c.close()

    t1 = threading.Thread(target=worker, args=("session-a", "a"))
    t2 = threading.Thread(target=worker, args=("session-b", "b"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Both threads should complete — at least one must succeed
    successes = sum(1 for r in results.values() if r is not None)
    failures = sum(1 for e in errors.values() if e is not None)
    assert successes >= 1, "At least one thread should succeed with stock=1"
    assert successes + failures == 2, "Both threads should complete (no crashes)"

    # Stock is advisory: both sessions may get the item (stock never decremented by add_item).
    # The invariant enforced by BEGIN IMMEDIATE is per-session consistency:
    # each session's cart_items quantity is correctly stored without corruption.
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT session_id, quantity FROM cart_items WHERE product_id = 'race-product'"
    ).fetchall()
    conn.close()

    # Each session that succeeded should have exactly qty=1
    for row in rows:
        assert row["quantity"] == 1, (
            f"Session {row['session_id']} has unexpected quantity {row['quantity']}"
        )


# --- 8.10 Test product deactivated after cart add ---


def test_product_deactivated_after_add(cart_db: sqlite3.Connection):
    """Product deactivated after cart add → appears in unavailable_items."""
    add_item(cart_db, SESSION_ID, "lavender-dream", 2)

    # Deactivate the product
    cart_db.execute("UPDATE products SET is_active = 0 WHERE id = 'lavender-dream'")
    cart_db.commit()

    cart = get_cart(cart_db, SESSION_ID)
    assert len(cart.items) == 0
    assert len(cart.unavailable_items) == 1
    assert cart.unavailable_items[0].product_id == "lavender-dream"
    assert cart.unavailable_items[0].product_name == "Lavender Dream"
    assert cart.unavailable_items[0].reason == "deactivated"


# --- 8.11 Test boundary values ---


class TestBoundaryValues:
    """Tests for exact boundary conditions on limits."""

    def test_add_at_limit_succeeds(self, cart_db: sqlite3.Connection):
        """Existing qty 7 + add 3 = 10 (at limit) succeeds."""
        add_item(cart_db, SESSION_ID, "ocean-breeze", 7)
        result = add_item(cart_db, SESSION_ID, "ocean-breeze", 3)
        assert result.cart.items[0].quantity == 10

    def test_add_over_limit_fails(self, cart_db: sqlite3.Connection):
        """Existing qty 10 + add 1 = 11 fails."""
        add_item(cart_db, SESSION_ID, "ocean-breeze", 10)
        with pytest.raises(QuantityLimitError):
            add_item(cart_db, SESSION_ID, "ocean-breeze", 1)

    def test_update_to_exactly_limit(self, cart_db: sqlite3.Connection):
        """update_quantity to exactly 10 succeeds."""
        add_item(cart_db, SESSION_ID, "ocean-breeze", 5)
        cart = update_quantity(cart_db, SESSION_ID, "ocean-breeze", 10)
        assert cart.items[0].quantity == 10

    def test_update_over_limit_fails(self, cart_db: sqlite3.Connection):
        """update_quantity to 11 fails."""
        add_item(cart_db, SESSION_ID, "ocean-breeze", 5)
        with pytest.raises(QuantityLimitError):
            update_quantity(cart_db, SESSION_ID, "ocean-breeze", 11)

    def test_cart_19_items_add_20th_succeeds(self, cart_db: sqlite3.Connection):
        """Cart with 19 distinct items, adding 20th succeeds."""
        for i in range(19):
            pid = f"boundary-product-{i:03d}"
            cart_db.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, "
                "is_active, created_at, updated_at) "
                "VALUES (?, ?, 1000, 50, 1, datetime('now'), datetime('now'))",
                (pid, f"Boundary Product {i}"),
            )
        cart_db.commit()

        for i in range(19):
            add_item(cart_db, SESSION_ID, f"boundary-product-{i:03d}", 1)

        # 20th succeeds
        result = add_item(cart_db, SESSION_ID, "lavender-dream", 1)
        assert result.created is True

    def test_cart_20_items_add_21st_fails(self, cart_db: sqlite3.Connection):
        """Cart with 20 distinct items, adding 21st fails."""
        for i in range(20):
            pid = f"limit-product-{i:03d}"
            cart_db.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, "
                "is_active, created_at, updated_at) "
                "VALUES (?, ?, 1000, 50, 1, datetime('now'), datetime('now'))",
                (pid, f"Limit Product {i}"),
            )
        cart_db.commit()

        for i in range(20):
            add_item(cart_db, SESSION_ID, f"limit-product-{i:03d}", 1)

        with pytest.raises(CartFullError):
            add_item(cart_db, SESSION_ID, "lavender-dream", 1)


# --- 8.12 Test add_item with quantity=0 ---


def test_add_item_quantity_zero_raises(cart_db: sqlite3.Connection):
    """add_item with quantity=0 raises error at service level."""
    with pytest.raises(ValueError, match="Quantity must be at least 1"):
        add_item(cart_db, SESSION_ID, "lavender-dream", 0)


# --- 8.13 Test concurrent per-item quantity limit ---


def test_concurrent_per_item_limit(db_path: str, app):
    """Two threads each adding qty=6 — final quantity never exceeds 10."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    now = datetime.now(UTC)

    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        ("shared-session", now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at) "
        "VALUES ('limit-race', 'Limit Race', 1000, 20, 1, datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    errors = []

    def worker():
        c = sqlite3.connect(db_path)
        c.execute("PRAGMA foreign_keys=ON")
        c.row_factory = sqlite3.Row
        try:
            add_item(c, "shared-session", "limit-race", 6)
        except QuantityLimitError:
            errors.append("limit")
        except Exception as e:
            errors.append(str(e))
        finally:
            c.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify final quantity — at least one thread must have succeeded
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT quantity FROM cart_items "
        "WHERE session_id = 'shared-session' AND product_id = 'limit-race'"
    ).fetchone()
    conn.close()

    assert row is not None, "At least one worker should have succeeded inserting the item"
    assert row[0] <= 10, f"Final quantity {row[0]} exceeds per-item limit of 10"
