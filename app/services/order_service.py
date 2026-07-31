"""Order service — checkout, retrieval, and state management.

All functions accept an explicit sqlite3.Connection and primitive parameters.
Routes destructure Pydantic models before calling these functions.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Literal, TypedDict

import structlog

from app.constants import MAX_LIMIT, MAX_PAGE, STATUS_TO_EMAIL_EVENT, tracking_url_for
from app.models.delivery import DeliveryInfo
from app.models.orders import OrderStatus
from app.services import delivery_service, pricing

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


class PaymentAlreadyPaidError(OrderServiceError):
    """Raised when attempting to mark an already-paid order as paid."""

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order {order_id} payment is already paid")


class WrongPaymentMethodError(OrderServiceError):
    """Raised when payment operation is invalid for the order's payment method."""

    def __init__(self, order_id: str, expected: str, actual: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order {order_id} payment method is '{actual}', expected '{expected}'")


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


class InvalidDeliveryOfficeError(OrderServiceError):
    """Raised when checkout references an office outside the courier catalogue."""

    def __init__(self, office_id: str, courier: str, reason: str = "not found") -> None:
        self.office_id = office_id
        self.courier = courier
        self.reason = reason
        super().__init__(f"Invalid {courier} office '{office_id}': {reason}")


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


class TrackingRequiredError(OrderServiceError):
    """Raised when shipping an order without required tracking data.

    Translated to a 422 with code TRACKING_REQUIRED at the route layer — this
    lives in the service (not a Pydantic validator) because the requirement is
    conditional on the target status and must use our error envelope
    (design Decision 21).
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Tracking information required when shipping: {', '.join(missing)}")


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
    items_total_cents: int
    shipping_cents: int
    customer_email: str
    customer_name: str | None
    delivery_method: str | None
    delivery_courier: str | None
    delivery_details: dict | None
    tracking_number: str | None
    tracking_carrier: str | None
    tracking_url: str | None
    locale: str
    notes: str | None
    payment_method: str
    payment_status: str
    stripe_checkout_session_id: str | None
    stripe_payment_intent_id: str | None
    analytics_consent: bool
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
    delivery: DeliveryInfo,
    customer_name: str | None = None,
    notes: str | None = None,
    user_id: str | None = None,
    locale: Locale = "en",
    admin_notification_email: str = "",
    payment_method: str = "cod",
    analytics_consent: bool = False,
) -> OrderData:
    """Convert cart to an order atomically.

    Uses BEGIN IMMEDIATE to serialize concurrent checkouts — prevents
    two sessions from decrementing stock past zero simultaneously.

    Validates stock, creates order with price snapshots, decrements stock,
    and clears cart items — all within an explicit transaction.

    `delivery` is JSON-serialized into `orders.delivery_details` with
    `ensure_ascii=False` so Cyrillic office/city names round-trip readably.
    `shipping_cents` is 0 in this change (real pricing lands in
    `shipping-pricing`); the value is server-enforced.
    """
    # Serialize delivery sub-object (office or door) into JSON blob.
    # ensure_ascii=False preserves Cyrillic — see HANDOFF gotcha #5.
    if delivery.method == "office" and delivery.office is not None:
        delivery_sub = delivery.office
        catalogue_office = delivery_service.get_office(
            delivery_sub.courier,
            delivery_sub.office_id,
            locale="bg",
        )
        if catalogue_office is None:
            raise InvalidDeliveryOfficeError(delivery_sub.office_id, delivery_sub.courier)
        if catalogue_office["type"] != delivery_sub.office_type:
            raise InvalidDeliveryOfficeError(
                delivery_sub.office_id,
                delivery_sub.courier,
                reason=f"office_type must be {catalogue_office['type']}",
            )
        delivery_details = delivery_sub.model_dump()
        delivery_details["office_name"] = catalogue_office["name"]
        delivery_details["office_type"] = catalogue_office["type"]
        delivery_courier = delivery_sub.courier
    else:
        delivery_sub = delivery.door
        delivery_details = delivery_sub.model_dump() if delivery_sub is not None else None
        delivery_courier = delivery_sub.courier if delivery_sub is not None else None

    delivery_details_json = json.dumps(delivery_details, ensure_ascii=False)

    conn.execute("BEGIN IMMEDIATE")
    try:
        name_expr = _localized_product_name(locale)
        # 1. Fetch cart items with product info
        cart_rows = conn.execute(
            f"""
            SELECT ci.product_id, ci.quantity, {name_expr}, p.price_cents,
                   p.discount_percent, p.discount_starts_at, p.discount_ends_at,
                   p.stock, p.is_active
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
        # Effective (discounted) price per row, computed once from a single `now`
        # so the total, the snapshot, and the returned items cannot disagree.
        # The customer is charged this amount; the floor clamp (>= 1 cent) keeps
        # order_items CHECK (price_cents > 0) satisfied.
        effective_prices = {
            row["product_id"]: pricing.effective_price_cents(
                row["price_cents"],
                row["discount_percent"],
                pricing.discount_is_active(
                    row["discount_percent"],
                    row["discount_starts_at"],
                    row["discount_ends_at"],
                    now,
                ),
            )
            for row in cart_rows
        }
        items_total_cents = sum(
            effective_prices[row["product_id"]] * row["quantity"] for row in cart_rows
        )
        # shipping_cents is a placeholder in this change — the shipping-pricing
        # follow-on adds real courier calculation + free-shipping threshold.
        shipping_cents = 0
        total_cents = items_total_cents + shipping_cents

        # Initial payment_status depends on payment method.
        initial_payment_status = "cod_pending" if payment_method == "cod" else "pending"

        conn.execute(
            """
            INSERT INTO orders (id, session_id, user_id, status, total_cents,
                               customer_email, customer_name,
                               delivery_method, delivery_courier, delivery_details,
                               locale, notes,
                               payment_method, payment_status,
                               analytics_consent, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                session_id,
                user_id,
                total_cents,
                customer_email,
                customer_name,
                delivery.method,
                delivery_courier,
                delivery_details_json,
                locale,
                notes,
                payment_method,
                initial_payment_status,
                1 if analytics_consent else 0,
                now,
                now,
            ),
        )

        # 4. Insert order items (snapshot effective prices and names)
        items: list[OrderItemData] = []
        for row in cart_rows:
            snapshot_price = effective_prices[row["product_id"]]
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, row["product_id"], row["name"], snapshot_price, row["quantity"]),
            )
            items.append(
                OrderItemData(
                    product_id=row["product_id"],
                    product_name=row["name"],
                    price_cents=snapshot_price,
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

        # 7. Durable outbox intent: queue customer email in the SAME transaction.
        # COD → 'placed' immediately. Card/bank_transfer → 'payment_pending'
        # (no thank-you language before payment confirmed — Decision 8).
        if payment_method == "cod":
            customer_event = STATUS_TO_EMAIL_EVENT["pending"]  # 'placed'
        else:
            customer_event = "payment_pending"
        if customer_event is not None:
            conn.execute(
                "INSERT INTO order_emails (order_id, event, recipient, status) "
                "VALUES (?, ?, ?, 'queued')",
                (order_id, customer_event, customer_email),
            )
        # Admin new-order alert rides the same outbox.
        conn.execute(
            "INSERT INTO order_emails (order_id, event, recipient, status) "
            "VALUES (?, 'admin_new_order', ?, 'queued')",
            (order_id, admin_notification_email or ""),
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
        items_total_cents=items_total_cents,
        shipping_cents=shipping_cents,
        customer_email=customer_email,
        customer_name=customer_name,
        delivery_method=delivery.method,
        delivery_courier=delivery_courier,
        delivery_details=json.loads(delivery_details_json) if delivery_details_json else None,
        tracking_number=None,
        tracking_carrier=None,
        tracking_url=None,
        locale=locale,
        notes=notes,
        payment_method=payment_method,
        payment_status=initial_payment_status,
        stripe_checkout_session_id=None,
        stripe_payment_intent_id=None,
        analytics_consent=analytics_consent,
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

    # Delivery details JSON blob → dict (or None for legacy rows).
    delivery_details_raw = row["delivery_details"] if "delivery_details" in row.keys() else None
    delivery_details: dict | None
    if delivery_details_raw:
        try:
            delivery_details = json.loads(delivery_details_raw)
        except json.JSONDecodeError:
            logger.warning(
                "order_delivery_details_invalid_json",
                order_id=order_id,
            )
            delivery_details = None
    else:
        delivery_details = None

    # shipping_cents column is added by shipping-pricing; safe-default to 0.
    shipping_cents = row["shipping_cents"] if "shipping_cents" in row.keys() else 0
    total_cents = row["total_cents"]
    items_total_cents = total_cents - shipping_cents

    row_keys = row.keys()
    return OrderData(
        id=row["id"],
        session_id=row["session_id"],
        user_id=row["user_id"],
        status=row["status"],
        total_cents=total_cents,
        items_total_cents=items_total_cents,
        shipping_cents=shipping_cents,
        customer_email=row["customer_email"],
        customer_name=row["customer_name"],
        delivery_method=row["delivery_method"] if "delivery_method" in row_keys else None,
        delivery_courier=row["delivery_courier"] if "delivery_courier" in row_keys else None,
        delivery_details=delivery_details,
        tracking_number=row["tracking_number"] if "tracking_number" in row_keys else None,
        tracking_carrier=row["tracking_carrier"] if "tracking_carrier" in row_keys else None,
        tracking_url=row["tracking_url"] if "tracking_url" in row_keys else None,
        locale=(row["locale"] if "locale" in row_keys and row["locale"] else "en"),
        notes=row["notes"],
        payment_method=row["payment_method"] if "payment_method" in row_keys else "cod",
        payment_status=row["payment_status"] if "payment_status" in row_keys else "cod_pending",
        stripe_checkout_session_id=(
            row["stripe_checkout_session_id"] if "stripe_checkout_session_id" in row_keys else None
        ),
        stripe_payment_intent_id=(
            row["stripe_payment_intent_id"] if "stripe_payment_intent_id" in row_keys else None
        ),
        analytics_consent=bool(row["analytics_consent"] if "analytics_consent" in row_keys else 0),
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
    payment_status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> OrderListData:
    """List all orders with optional status/payment_status filter (admin — no ownership check).

    Pagination values are clamped to MAX_PAGE/MAX_LIMIT bounds.
    """
    if page < 1:
        page = 1
    page = min(page, MAX_PAGE)
    if limit < 1:
        limit = 1
    limit = min(limit, MAX_LIMIT)

    offset = (page - 1) * limit

    conditions = []
    params: list = []
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if payment_status is not None:
        conditions.append("payment_status = ?")
        params.append(payment_status)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

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
    tracking_number: str | None = None,
    tracking_carrier: str | None = None,
    tracking_url: str | None = None,
) -> OrderData:
    """Update order status with state machine validation.

    When transitioning to "shipped", tracking_number and tracking_carrier are
    required (raises TrackingRequiredError → 422 TRACKING_REQUIRED). tracking_url
    is auto-generated from a known carrier when not supplied, and persisted
    alongside the status. Restores stock on cancellation (from pending/confirmed).
    """
    row = conn.execute(
        "SELECT id, status, payment_method FROM orders WHERE id = ?", (order_id,)
    ).fetchone()

    if not row:
        raise OrderNotFoundError(order_id)

    current_status = row["status"]
    payment_method = row["payment_method"] if "payment_method" in row.keys() else "cod"

    # Validate transition
    if new_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise InvalidStateTransitionError(order_id, current_status, new_status)

    if new_status == "shipped":
        # Tracking is required on ship; url is optional (auto-generated below).
        missing = []
        if not tracking_number:
            missing.append("tracking_number")
        if not tracking_carrier:
            missing.append("tracking_carrier")
        if missing:
            raise TrackingRequiredError(missing)

        # Auto-generate the URL from a known carrier when the admin didn't paste one.
        if not tracking_url:
            tracking_url = tracking_url_for(tracking_carrier, tracking_number)

        conn.execute(
            """
            UPDATE orders
            SET status = ?, tracking_number = ?, tracking_carrier = ?, tracking_url = ?
            WHERE id = ?
            """,
            (new_status, tracking_number, tracking_carrier, tracking_url, order_id),
        )
    else:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (new_status, order_id),
        )

    # COD: auto-advance payment_status to 'paid' on delivery (Decision 2).
    # Cash is collected at delivery by the courier — no manual step needed.
    if new_status == "delivered" and payment_method == "cod":
        conn.execute(
            "UPDATE orders SET payment_status = 'paid' WHERE id = ?",
            (order_id,),
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


def mark_bank_transfer_paid(
    conn: sqlite3.Connection,
    order_id: str,
) -> OrderData:
    """Mark a bank_transfer order's payment_status as 'paid'.

    Raises WrongPaymentMethodError if the order is not bank_transfer.
    Raises PaymentAlreadyPaidError if already paid.
    Raises OrderNotFoundError if not found.
    """
    row = conn.execute(
        "SELECT id, payment_method, payment_status FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if not row:
        raise OrderNotFoundError(order_id)
    if row["payment_method"] != "bank_transfer":
        raise WrongPaymentMethodError(order_id, "bank_transfer", row["payment_method"])
    if row["payment_status"] == "paid":
        raise PaymentAlreadyPaidError(order_id)

    conn.execute(
        "UPDATE orders SET payment_status = 'paid' WHERE id = ?",
        (order_id,),
    )
    conn.execute(
        "INSERT OR IGNORE INTO order_emails (order_id, event, recipient, status)"
        " VALUES (?, 'placed', (SELECT customer_email FROM orders WHERE id = ?), 'queued')",
        (order_id, order_id),
    )
    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order
