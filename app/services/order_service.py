"""Order service — checkout, retrieval, and state management.

All functions accept an explicit sqlite3.Connection and primitive parameters.
Routes destructure Pydantic models before calling these functions.
"""

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Literal, TypedDict

import structlog

from app.constants import MAX_LIMIT, MAX_PAGE
from app.models.orders import OrderStatus

logger = structlog.get_logger(__name__)

# SQLite-compatible datetime format
_DT_FMT = "%Y-%m-%d %H:%M:%S"

# Valid state transitions for orders
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}

Locale = Literal["en", "bg"]


def _localized_product_name(locale: Locale) -> str:
    """Return a safe SQL expression for locale-resolved product names."""
    if locale == "bg":
        return "COALESCE(NULLIF(p.name_bg, ''), p.name_en, '') AS name"
    return "COALESCE(NULLIF(p.name_en, ''), p.name_bg, '') AS name"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OrderServiceError(Exception):
    """Base class for all order service errors."""


class EmptyCartError(OrderServiceError):
    """Raised when cart has no items at checkout."""


class InsufficientStockError(OrderServiceError):
    """Raised when a product does not have enough stock."""

    def __init__(self, failures: list[dict]) -> None:
        self.failures = failures
        messages = [
            f"{f['product_id']}: requested {f['requested']}, available {f['available']}"
            for f in failures
        ]
        super().__init__(f"Insufficient stock: {'; '.join(messages)}")


class ProductUnavailableError(OrderServiceError):
    """Raised when a product is deactivated."""

    def __init__(self, failures: list[dict]) -> None:
        self.failures = failures
        messages = [f"{f['product_id']} ({f['product_name']})" for f in failures]
        super().__init__(f"Product unavailable: {', '.join(messages)}")


class InvalidStateTransitionError(OrderServiceError):
    """Raised when an invalid order state transition is attempted."""

    def __init__(self, order_id: str, current_status: str, requested_status: str) -> None:
        self.order_id = order_id
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid state transition from '{current_status}' to '{requested_status}'"
        )


class OrderNotFoundError(OrderServiceError):
    """Raised when an order cannot be found (or access denied)."""

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order not found: {order_id}")


# ---------------------------------------------------------------------------
# TypedDict return types
# ---------------------------------------------------------------------------


class OrderItemData(TypedDict):
    product_id: str
    product_name: str
    price_cents: int
    quantity: int


class OrderData(TypedDict):
    id: str
    session_id: str
    user_id: str | None
    status: str
    total_cents: int
    customer_email: str
    customer_name: str | None
    shipping_address: str | None
    notes: str | None
    created_at: str
    updated_at: str
    items: list[OrderItemData]


class OrderListData(TypedDict):
    items: list[OrderData]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def checkout(
    conn: sqlite3.Connection,
    session_id: str,
    customer_email: str,
    customer_name: str | None = None,
    shipping_address: str | None = None,
    notes: str | None = None,
    user_id: str | None = None,
    locale: Locale = "en",
) -> OrderData:
    """Convert cart to an order atomically.

    Uses BEGIN IMMEDIATE to serialize concurrent checkouts — prevents
    two sessions from decrementing stock past zero simultaneously.

    Validates stock, creates order with price snapshots, decrements stock,
    and clears cart items — all within an explicit transaction.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        name_expr = _localized_product_name(locale)
        # 1. Fetch cart items with product info
        cart_rows = conn.execute(
            f"""
            SELECT ci.product_id, ci.quantity, {name_expr}, p.price_cents, p.stock, p.is_active
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.session_id = ?
            """,  # noqa: S608 - locale selects a fixed SQL expression above.
            (session_id,),
        ).fetchall()

        if not cart_rows:
            raise EmptyCartError("Cart is empty")

        # 2. Batch-validate all items (collect ALL failures)
        unavailable_failures: list[dict] = []
        stock_failures: list[dict] = []

        for row in cart_rows:
            if not row["is_active"]:
                unavailable_failures.append(
                    {
                        "product_id": row["product_id"],
                        "product_name": row["name"],
                    }
                )
            elif row["stock"] < row["quantity"]:
                stock_failures.append(
                    {
                        "product_id": row["product_id"],
                        "requested": row["quantity"],
                        "available": row["stock"],
                    }
                )

        # Raise unavailable first (more severe), then stock issues
        if unavailable_failures:
            raise ProductUnavailableError(unavailable_failures)
        if stock_failures:
            raise InsufficientStockError(stock_failures)

        # 3. Create order
        order_id = str(uuid.uuid4())
        now = datetime.now(UTC).strftime(_DT_FMT)
        total_cents = sum(row["price_cents"] * row["quantity"] for row in cart_rows)

        conn.execute(
            """
            INSERT INTO orders (id, session_id, user_id, status, total_cents,
                               customer_email, customer_name, shipping_address, notes,
                               created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                session_id,
                user_id,
                total_cents,
                customer_email,
                customer_name,
                shipping_address,
                notes,
                now,
                now,
            ),
        )

        # 4. Insert order items (snapshot prices and names)
        items: list[OrderItemData] = []
        for row in cart_rows:
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, row["product_id"], row["name"], row["price_cents"], row["quantity"]),
            )
            items.append(
                OrderItemData(
                    product_id=row["product_id"],
                    product_name=row["name"],
                    price_cents=row["price_cents"],
                    quantity=row["quantity"],
                )
            )

        # 5. Decrement stock
        for row in cart_rows:
            try:
                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (row["quantity"], row["product_id"]),
                )
            except sqlite3.IntegrityError as e:
                # CHECK (stock >= 0) constraint violated — race condition.
                raise InsufficientStockError(
                    [
                        {
                            "product_id": row["product_id"],
                            "requested": row["quantity"],
                            "available": 0,
                        }
                    ]
                ) from e

        # 6. Clear cart items for products included in this order
        product_ids = [row["product_id"] for row in cart_rows]
        placeholders = ",".join("?" * len(product_ids))
        conn.execute(
            f"DELETE FROM cart_items WHERE session_id = ? AND product_id IN ({placeholders})",
            [session_id, *product_ids],
        )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return OrderData(
        id=order_id,
        session_id=session_id,
        user_id=user_id,
        status="pending",
        total_cents=total_cents,
        customer_email=customer_email,
        customer_name=customer_name,
        shipping_address=shipping_address,
        notes=notes,
        created_at=now,
        updated_at=now,
        items=items,
    )


def _fetch_order_with_items(conn: sqlite3.Connection, order_id: str) -> OrderData | None:
    """Fetch an order and its items. Returns None if not found."""
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        return None

    item_rows = conn.execute(
        "SELECT product_id, product_name, price_cents, quantity"
        " FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()

    items = [
        OrderItemData(
            product_id=ir["product_id"],
            product_name=ir["product_name"],
            price_cents=ir["price_cents"],
            quantity=ir["quantity"],
        )
        for ir in item_rows
    ]

    return OrderData(
        id=row["id"],
        session_id=row["session_id"],
        user_id=row["user_id"],
        status=row["status"],
        total_cents=row["total_cents"],
        customer_email=row["customer_email"],
        customer_name=row["customer_name"],
        shipping_address=row["shipping_address"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        items=items,
    )


def get_order(
    conn: sqlite3.Connection,
    order_id: str,
    session_id: str,
    user_id: str | None = None,
) -> OrderData:
    """Fetch order with access control. Returns 404-style error for non-owners."""
    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)

    # Access control: session_id match OR user_id match
    owns_by_session = order["session_id"] == session_id
    owns_by_user = user_id is not None and order["user_id"] == user_id

    if not owns_by_session and not owns_by_user:
        # Never expose 403 — always 404 to prevent enumeration
        raise OrderNotFoundError(order_id)

    return order


def get_order_admin(conn: sqlite3.Connection, order_id: str) -> OrderData:
    """Fetch order without ownership check (admin auth enforced at route level)."""
    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def list_orders(
    conn: sqlite3.Connection,
    session_id: str,
    user_id: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> OrderListData:
    """List orders for a session/user with pagination.

    When user_id is provided, filter by user_id only (captures all sessions).
    When user_id is None, filter by session_id only.
    Pagination values are clamped to MAX_PAGE/MAX_LIMIT bounds.
    """
    if page < 1:
        page = 1
    page = min(page, MAX_PAGE)
    if limit < 1:
        raise ValueError("limit must be at least 1")
    limit = min(limit, MAX_LIMIT)

    offset = (page - 1) * limit

    if user_id is not None:
        where_clause = "WHERE user_id = ?"
        params: list = [user_id]
    else:
        where_clause = "WHERE session_id = ?"
        params = [session_id]

    # Total count
    total = conn.execute(f"SELECT COUNT(*) FROM orders {where_clause}", params).fetchone()[0]

    # Paginated results
    rows = conn.execute(
        f"SELECT id FROM orders {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    items: list[OrderData] = []
    for row in rows:
        order = _fetch_order_with_items(conn, row["id"])
        if order is not None:
            items.append(order)

    return OrderListData(items=items, total=total, page=page, limit=limit)


def list_orders_admin(
    conn: sqlite3.Connection,
    status: OrderStatus | None = None,
    page: int = 1,
    limit: int = 20,
) -> OrderListData:
    """List all orders with optional status filter (admin — no ownership check).

    Pagination values are clamped to MAX_PAGE/MAX_LIMIT bounds.
    """
    if page < 1:
        page = 1
    page = min(page, MAX_PAGE)
    if limit < 1:
        limit = 1
    limit = min(limit, MAX_LIMIT)

    offset = (page - 1) * limit

    if status is not None:
        where_clause = "WHERE status = ?"
        params: list = [status]
    else:
        where_clause = ""
        params = []

    total = conn.execute(f"SELECT COUNT(*) FROM orders {where_clause}", params).fetchone()[0]

    rows = conn.execute(
        f"SELECT id FROM orders {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    items: list[OrderData] = []
    for row in rows:
        order = _fetch_order_with_items(conn, row["id"])
        if order is not None:
            items.append(order)

    return OrderListData(items=items, total=total, page=page, limit=limit)


def update_status(
    conn: sqlite3.Connection,
    order_id: str,
    new_status: OrderStatus,
) -> OrderData:
    """Update order status with state machine validation.

    Restores stock on cancellation (from pending or confirmed).
    """
    row = conn.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not row:
        raise OrderNotFoundError(order_id)

    current_status = row["status"]

    # Validate transition
    if new_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise InvalidStateTransitionError(order_id, current_status, new_status)

    # Update status (updated_at handled by trigger)
    conn.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id),
    )

    # Restore stock on cancellation
    if new_status == "cancelled":
        item_rows = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        for item in item_rows:
            cursor = conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
            if cursor.rowcount == 0:
                logger.warning(
                    "Could not restore stock for missing product",
                    product_id=item["product_id"],
                    order_id=order_id,
                )

    # Log admin action
    logger.info(
        "Order status updated",
        order_id=order_id,
        old_status=current_status,
        new_status=new_status,
    )

    # Return updated order
    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order
