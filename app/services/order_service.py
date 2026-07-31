"""Order service — checkout, retrieval, and state management.

All functions accept an explicit sqlite3.Connection and primitive parameters.
Routes destructure Pydantic models before calling these functions.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Literal, TypedDict, get_args

import structlog

from app.constants import (
    FREE_SHIPPING_THRESHOLD_CENTS,
    MAX_LIMIT,
    MAX_PAGE,
    SHIPPING_CENTS_MAX,
    STATUS_TO_EMAIL_EVENT,
    ShippingPriceSource,
    tracking_url_for,
)
from app.models.delivery import DeliveryInfo
from app.models.orders import OrderStatus
from app.services import delivery_service, delivery_settings_service, pricing

logger = structlog.get_logger(__name__)

# SQLite-compatible datetime format
_DT_FMT = "%Y-%m-%d %H:%M:%S"

# Runtime whitelist for the shipping price-source provenance column, derived from
# the Literal so it can never drift from the type (same pattern as OrderStatus).
_VALID_PRICE_SOURCES: frozenset[str] = frozenset(get_args(ShippingPriceSource))

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


def _normalize_quoted_at(value: str | None) -> str | None:
    """Keep `quoted_at` only if it parses as our SQLite timestamp format.

    The client echoes this back from the quote; it is audit metadata, so we
    drop anything that isn't a well-formed `_DT_FMT` string rather than persist
    a fabricated value (review W3). None (no quote timestamp) is passed through.
    """
    if value is None:
        return None
    try:
        datetime.strptime(value, _DT_FMT)
    except ValueError:
        return None
    return value


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


class InvalidShippingPriceError(OrderServiceError):
    """Raised when a client-submitted shipping_cents is out of the accepted range.

    Translated to a 422 with code INVALID_SHIPPING_PRICE at the route layer.
    Server range-validates rather than trusting the frontend (parent Decision 16).
    """

    def __init__(self, shipping_cents: int, max_cents: int) -> None:
        self.shipping_cents = shipping_cents
        self.max_cents = max_cents
        super().__init__(
            f"shipping_cents {shipping_cents} is outside the accepted range [0, {max_cents}]"
        )


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


class DeliveryMethodUnavailableError(OrderServiceError):
    """Raised when checkout uses an admin-disabled courier/method pair."""

    def __init__(self, courier: str, method: str) -> None:
        self.courier = courier
        self.method = method
        super().__init__(f"{courier} {method} delivery is currently unavailable")


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


def _create_speedy_waybill(row: sqlite3.Row) -> tuple[str, str | None]:
    """Create a Speedy waybill from an order row; return (tracking_number, label_url).

    Raises speedy_client.ShipmentCreationError on failure (surfaced to admin as a
    502 by the route). Called inside the ship transaction BEFORE the UPDATE, so a
    failure aborts the transaction (design Decision 3). Imported lazily to keep
    Layer-1 order state free of a hard courier-module dependency at import time.
    """
    from app.config import get_settings
    from app.services import speedy_client

    settings = get_settings()
    details_raw = row["delivery_details"] if "delivery_details" in row.keys() else None
    details: dict = {}
    if details_raw:
        try:
            details = json.loads(details_raw)
        except json.JSONDecodeError:
            details = {}

    method = row["delivery_method"] if "delivery_method" in row.keys() else None
    recipient_name = details.get("office_name") or row["customer_name"] or "Recipient"
    phone = details.get("phone") or ""
    # COD orders collect the full order total (items + shipping) on delivery.
    payment_method = row["payment_method"] if "payment_method" in row.keys() else "cod"
    payment_status = row["payment_status"] if "payment_status" in row.keys() else ""
    cod_cents = row["total_cents"] if payment_method == "cod" and payment_status != "paid" else None

    if method == "office":
        tracking = speedy_client.create_shipment_sync(
            client_id=settings.speedy_client_id,
            recipient_name=recipient_name,
            recipient_phone=phone,
            weight_grams=0,
            username=settings.speedy_api_username,
            password=settings.speedy_api_password.get_secret_value(),
            order_ref=row["id"],
            recipient_office_id=details.get("office_id"),
            recipient_city=details.get("city"),
            cod_amount_cents=cod_cents,
        )
    else:
        tracking = speedy_client.create_shipment_sync(
            client_id=settings.speedy_client_id,
            recipient_name=recipient_name,
            recipient_phone=phone,
            weight_grams=0,
            username=settings.speedy_api_username,
            password=settings.speedy_api_password.get_secret_value(),
            order_ref=row["id"],
            recipient_city=details.get("city"),
            recipient_postcode=details.get("postal_code"),
            recipient_street=details.get("street"),
            recipient_building=details.get("building"),
            cod_amount_cents=cod_cents,
        )
    return tracking, None


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
    shipping_price_source: str
    shipping_is_fallback: bool
    shipping_quoted_at: str | None
    customer_email: str
    customer_name: str | None
    delivery_method: str | None
    delivery_courier: str | None
    delivery_details: dict | None
    tracking_number: str | None
    tracking_carrier: str | None
    tracking_url: str | None
    courier_status: str | None
    label_url: str | None
    locale: str
    notes: str | None
    payment_method: str
    payment_status: str
    stripe_checkout_session_id: str | None
    stripe_payment_intent_id: str | None
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
    shipping_cents: int = 0,
    shipping_price_source: str = "live",
    shipping_is_fallback: bool = False,
    shipping_quoted_at: str | None = None,
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
        if not delivery_settings_service.is_delivery_method_enabled(
            delivery_sub.courier,
            "office",
        ):
            raise DeliveryMethodUnavailableError(delivery_sub.courier, "office")
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
        if delivery_sub is not None and not delivery_settings_service.is_delivery_method_enabled(
            delivery_sub.courier,
            "door",
        ):
            raise DeliveryMethodUnavailableError(delivery_sub.courier, "door")
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
        # Server-enforce shipping (parent Decision 16 — never trust the client).
        # 1. Free shipping short-circuit: items ≥ €50 forces 0¢ and normalizes
        #    provenance to live/non-fallback (a free order was never "guessed").
        # 2. Otherwise range-validate the client-submitted shipping_cents.
        #
        # ACCEPTED (review W2): the range check admits shipping_cents == 0 on a
        # sub-€50 order, so a scripted client can under-pay shipping. This is a
        # deliberate MVP tradeoff — parent Decision 16 chose range-check over
        # signed price tokens, and the dominant COD flow (see design.md) means a
        # human confirms every order before dispatch, catching a 0¢ shipping line.
        # Server-side re-quoting is deferred to Phase C (reconciliation).
        if items_total_cents >= FREE_SHIPPING_THRESHOLD_CENTS:
            shipping_cents = 0
            shipping_price_source = "live"
            shipping_is_fallback = False
            shipping_quoted_at = None
        else:
            if not (0 <= shipping_cents <= SHIPPING_CENTS_MAX):
                raise InvalidShippingPriceError(shipping_cents, SHIPPING_CENTS_MAX)
            # Harden provenance (review W3): the client echoes these back from the
            # quote, but they are audit metadata for reconciliation — never trust
            # them verbatim. Reject an unknown source, then DERIVE is_fallback from
            # it (a "live" quote is never a fallback; anything else is) so a client
            # cannot relabel a flat/fallback price as a clean live one. quoted_at is
            # only kept when it parses as our timestamp format; garbage is dropped.
            if shipping_price_source not in _VALID_PRICE_SOURCES:
                raise InvalidShippingPriceError(shipping_cents, SHIPPING_CENTS_MAX)
            shipping_is_fallback = shipping_price_source != "live"
            shipping_quoted_at = _normalize_quoted_at(shipping_quoted_at)
        total_cents = items_total_cents + shipping_cents

        # Initial payment_status depends on payment method.
        initial_payment_status = "cod_pending" if payment_method == "cod" else "pending"

        conn.execute(
            """
            INSERT INTO orders (id, session_id, user_id, status, total_cents,
                               customer_email, customer_name,
                               shipping_cents, shipping_price_source,
                               shipping_is_fallback, shipping_quoted_at,
                               delivery_method, delivery_courier, delivery_details,
                               locale, notes,
                               payment_method, payment_status,
                               created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                session_id,
                user_id,
                total_cents,
                customer_email,
                customer_name,
                shipping_cents,
                shipping_price_source,
                1 if shipping_is_fallback else 0,
                shipping_quoted_at,
                delivery.method,
                delivery_courier,
                delivery_details_json,
                locale,
                notes,
                payment_method,
                initial_payment_status,
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
        shipping_price_source=shipping_price_source,
        shipping_is_fallback=shipping_is_fallback,
        shipping_quoted_at=shipping_quoted_at,
        customer_email=customer_email,
        customer_name=customer_name,
        delivery_method=delivery.method,
        delivery_courier=delivery_courier,
        delivery_details=json.loads(delivery_details_json) if delivery_details_json else None,
        tracking_number=None,
        tracking_carrier=None,
        tracking_url=None,
        courier_status=None,
        label_url=None,
        locale=locale,
        notes=notes,
        payment_method=payment_method,
        payment_status=initial_payment_status,
        stripe_checkout_session_id=None,
        stripe_payment_intent_id=None,
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
    row_keys = row.keys()
    shipping_cents = row["shipping_cents"] if "shipping_cents" in row_keys else 0
    total_cents = row["total_cents"]
    items_total_cents = total_cents - shipping_cents
    # Provenance columns default to live/non-fallback for legacy rows.
    shipping_price_source = (
        row["shipping_price_source"]
        if "shipping_price_source" in row_keys and row["shipping_price_source"]
        else "live"
    )
    shipping_is_fallback = bool(
        row["shipping_is_fallback"] if "shipping_is_fallback" in row_keys else 0
    )
    shipping_quoted_at = row["shipping_quoted_at"] if "shipping_quoted_at" in row_keys else None

    return OrderData(
        id=row["id"],
        session_id=row["session_id"],
        user_id=row["user_id"],
        status=row["status"],
        total_cents=total_cents,
        items_total_cents=items_total_cents,
        shipping_cents=shipping_cents,
        shipping_price_source=shipping_price_source,
        shipping_is_fallback=shipping_is_fallback,
        shipping_quoted_at=shipping_quoted_at,
        customer_email=row["customer_email"],
        customer_name=row["customer_name"],
        delivery_method=row["delivery_method"] if "delivery_method" in row_keys else None,
        delivery_courier=row["delivery_courier"] if "delivery_courier" in row_keys else None,
        delivery_details=delivery_details,
        tracking_number=row["tracking_number"] if "tracking_number" in row_keys else None,
        tracking_carrier=row["tracking_carrier"] if "tracking_carrier" in row_keys else None,
        tracking_url=row["tracking_url"] if "tracking_url" in row_keys else None,
        courier_status=row["courier_status"] if "courier_status" in row_keys else None,
        label_url=row["label_url"] if "label_url" in row_keys else None,
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

    Speedy waybill automation (speedy-integration Decision 3): on the
    confirmed→shipped transition, when the order's courier is Speedy AND no
    tracking number was supplied, a waybill is created via the Speedy API and its
    returned id becomes the tracking number. Creation runs BEFORE the UPDATE, so a
    failure raises ShipmentCreationError and the transaction never commits — the
    order stays `confirmed`, never `shipped` without a waybill. A manually supplied
    tracking number skips the courier call (idempotent re-ship, and manual/offline
    fallback both preserved).
    """
    row = conn.execute(
        "SELECT id, status, payment_method, delivery_method, delivery_courier,"
        " delivery_details, customer_name, total_cents, shipping_cents, payment_status"
        " FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()

    if not row:
        raise OrderNotFoundError(order_id)

    current_status = row["status"]
    payment_method = row["payment_method"] if "payment_method" in row.keys() else "cod"

    # Validate transition
    if new_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise InvalidStateTransitionError(order_id, current_status, new_status)

    label_url: str | None = None

    if new_status == "shipped":
        # Speedy waybill automation: create the waybill and birth the tracking
        # number ourselves when this is a Speedy order with no number supplied.
        # Runs before the tracking-required guard so a Speedy ship needs no manual
        # number, but a non-Speedy / manual ship still must supply one.
        delivery_courier = row["delivery_courier"] if "delivery_courier" in row.keys() else None
        if not tracking_number and delivery_courier == "speedy":
            tracking_number, label_url = _create_speedy_waybill(row)
            tracking_carrier = tracking_carrier or "speedy"

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
            SET status = ?, tracking_number = ?, tracking_carrier = ?, tracking_url = ?,
                label_url = COALESCE(?, label_url)
            WHERE id = ?
            """,
            (new_status, tracking_number, tracking_carrier, tracking_url, label_url, order_id),
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
