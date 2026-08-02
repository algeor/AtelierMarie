"""Order service — checkout, retrieval, and state management.

All functions accept an explicit psycopg.Connection and primitive parameters.
Routes destructure Pydantic models before calling these functions.
"""

import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypedDict, get_args

import psycopg
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
from app.models.orders import InvoiceProfile, OrderStatus
from app.services import (
    accounting_config_service,
    delivery_service,
    delivery_settings_service,
    pricing,
)

logger = structlog.get_logger(__name__)

# SQLite-compatible datetime format
_DT_FMT = "%Y-%m-%d %H:%M:%S"
_ORDER_NUMBER_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Runtime whitelist for the shipping price-source provenance column, derived from
# the Literal so it can never drift from the type (same pattern as OrderStatus).
_VALID_PRICE_SOURCES: frozenset[str] = frozenset(get_args(ShippingPriceSource))
_DEFAULT_SHIPMENT_WEIGHT_GRAMS = 300


class AccountingAdminFields(TypedDict):
    accounting_readiness_status: str
    document_reference_status: str
    payment_reconciliation_status: str
    payout_reconciliation_status: str
    cod_settlement_status: str
    blocking_exception_count: int
    finance_hub_links: dict[str, str | None] | None


def _generate_order_number(conn: psycopg.Connection) -> str:
    """Generate AM-xxxxxx public order numbers with bounded collision retries."""
    for _ in range(10):
        code = "AM-" + "".join(secrets.choice(_ORDER_NUMBER_ALPHABET) for _ in range(6))
        exists = conn.execute("SELECT 1 FROM orders WHERE order_number = %s", (code,)).fetchone()
        if exists is None:
            return code
    msg = "Could not generate a unique order number"
    raise OrderServiceError(msg)


def _generate_payment_return_token(conn: psycopg.Connection) -> str:
    """Generate a bearer token used for payment return/status flows."""
    for _ in range(10):
        token = secrets.token_urlsafe(24)
        exists = conn.execute(
            "SELECT 1 FROM orders WHERE payment_return_token = %s",
            (token,),
        ).fetchone()
        if exists is None:
            return token
    msg = "Could not generate a unique payment return token"
    raise OrderServiceError(msg)


# Valid state transitions for orders
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"shipped", "cancelled"},
    "shipped": {"delivered", "return_in_transit"},
    "delivered": {"return_in_transit"},
    "return_in_transit": {"returned"},
    "returned": set(),
    "cancelled": set(),
}

ADMIN_REVIEW_FILTERS = frozenset(
    {
        "abandoned_payment",
        "uncollected_refused",
        "refund_pending",
        "inspection_pending",
        "courier_claim_follow_up",
        "cod_settlement_pending",
    }
)

ADMIN_ACCOUNTING_FILTERS = frozenset(
    {
        "missing_document_reference",
        "unresolved_exception",
        "payout_mismatch",
        "cod_settlement_pending",
        "refund_document_missing",
        "vat_review_required",
        "missing_batch_assignment",
        "missing_inventory_movement",
        "missing_cogs_row",
        "valuation_exception",
        "return_inventory_review_pending",
    }
)

_PAID_ACCOUNTING_STATUSES = {"paid", "partially_refunded", "refunded"}

_LEDGER_MANAGED_MODE = "ledger_managed"
_FINISHED_GOOD_UOM = "unit"

Locale = Literal["en", "bg"]


def _localized_product_name(locale: Locale) -> str:
    """Return a safe SQL expression for locale-resolved product names."""
    if locale == "bg":
        return "COALESCE(NULLIF(p.name_bg, ''), p.name_en, '') AS name"
    return "COALESCE(NULLIF(p.name_en, ''), p.name_bg, '') AS name"


def _fmt_ts(value: object) -> str | None:
    """Render a timestamp column read as the canonical `_DT_FMT` string.

    Postgres TIMESTAMPTZ columns come back from psycopg (dict_row) as
    ``datetime`` objects, but OrderData/OrderResponse declare these fields as
    ``str``. Timestamps are written as `_DT_FMT` strings on INSERT, so we
    normalise reads to the same shape. ``None`` passes through; an existing
    string (legacy/echoed value) is returned unchanged.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


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


def _decode_json_dict(value: str | None, *, order_id: str, field: str) -> dict | None:
    if not value:
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        logger.warning("order_json_field_invalid", order_id=order_id, field=field)
        return None
    return decoded if isinstance(decoded, dict) else None


def _order_item_key(order_id: str, product_id: str) -> str:
    return f"{order_id}:{product_id}"


def _ledger_modes_for_products(conn: psycopg.Connection, product_ids: list[str]) -> dict[str, str]:
    if not product_ids:
        return {}
    placeholders = ",".join("%s" for _ in product_ids)
    rows = conn.execute(
        f"""
        SELECT product_id, inventory_mode
        FROM product_inventory_profiles
        WHERE product_id IN ({placeholders})
        """,  # noqa: S608 - placeholders are generated from product_ids length.
        product_ids,
    ).fetchall()
    return {row["product_id"]: row["inventory_mode"] for row in rows}


def _product_inventory_mode(conn: psycopg.Connection, product_id: str) -> str:
    row = conn.execute(
        "SELECT inventory_mode FROM product_inventory_profiles WHERE product_id = %s",
        (product_id,),
    ).fetchone()
    return row["inventory_mode"] if row is not None else "legacy"


def _is_ledger_managed_mode(mode: str | None) -> bool:
    return mode == _LEDGER_MANAGED_MODE


def _insert_inventory_exception(
    conn: psycopg.Connection,
    *,
    exception_type: str,
    message: str,
    target_type: str,
    target_id: str,
    source_type: str,
    source_id: str,
    severity: str = "warning",
) -> None:
    exists = conn.execute(
        """
        SELECT 1
        FROM inventory_exceptions
        WHERE exception_type = %s
          AND target_type = %s
          AND target_id = %s
          AND source_type = %s
          AND source_id = %s
          AND status = 'open'
        """,
        (exception_type, target_type, target_id, source_type, source_id),
    ).fetchone()
    if exists is not None:
        return
    conn.execute(
        """
        INSERT INTO inventory_exceptions (
            id, exception_type, severity, target_type, target_id,
            source_type, source_id, message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(uuid.uuid4()),
            exception_type,
            severity,
            target_type,
            target_id,
            source_type,
            source_id,
            message,
        ),
    )


def _record_finished_good_movement(
    conn: psycopg.Connection,
    *,
    product_id: str,
    movement_type: str,
    quantity_delta: int | float,
    source_type: str,
    source_id: str,
    order_id: str | None = None,
    order_item_key: str | None = None,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    reason: str | None = None,
    notes: str | None = None,
    reversal_of_movement_id: str | None = None,
    review_state: str = "reviewed",
    occurred_at: str | None = None,
    metadata: dict[str, Any] | None = None,
    update_stock_cache: bool = True,
) -> str:
    if float(quantity_delta) == 0:
        raise OrderServiceError("Inventory movement quantity must not be zero")
    movement_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO inventory_movements (
            id, item_type, item_id, movement_type, quantity_delta, uom,
            source_type, source_id, product_id, order_id, order_item_key,
            actor_user_id, actor_email, reason, notes, reversal_of_movement_id,
            review_state, occurred_at, metadata_json
        ) VALUES (%s, 'finished_good', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            movement_id,
            product_id,
            movement_type,
            quantity_delta,
            _FINISHED_GOOD_UOM,
            source_type,
            source_id,
            product_id,
            order_id,
            order_item_key,
            actor_user_id,
            actor_email,
            reason,
            notes,
            reversal_of_movement_id,
            review_state,
            occurred_at or datetime.now(UTC).strftime(_DT_FMT),
            json.dumps(metadata, separators=(",", ":")) if metadata else None,
        ),
    )
    if update_stock_cache:
        cursor = conn.execute(
            "UPDATE products SET stock = stock + %s WHERE id = %s",
            (quantity_delta, product_id),
        )
        if cursor.rowcount == 0:
            raise ProductUnavailableError([{"product_id": product_id, "product_name": product_id}])
    return movement_id


def _sale_issue_movement(
    conn: psycopg.Connection,
    *,
    order_id: str,
    product_id: str,
) -> dict | None:
    return conn.execute(
        """
        SELECT *
        FROM inventory_movements
        WHERE order_id = %s
          AND product_id = %s
          AND order_item_key = %s
          AND movement_type = 'sale_issue'
        ORDER BY occurred_at DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (order_id, product_id, _order_item_key(order_id, product_id)),
    ).fetchone()


def _accounting_admin_fields(
    conn: psycopg.Connection,
    *,
    order_id: str,
    total_cents: int,
    payment_method: str,
    payment_status: str,
    finance_period_id: str | None,
    stripe_payment_intent_id: str | None,
    fallback_readiness_status: str,
) -> AccountingAdminFields:
    """Compute admin display flags from accounting evidence without guessing policy."""

    exception_rows = conn.execute(
        """
        SELECT period_id, exception_type, severity
        FROM finance_exceptions
        WHERE target_type = 'order'
          AND target_id = %s
          AND status = 'open'
        """,
        (order_id,),
    ).fetchall()
    blocking_exception_count = sum(1 for row in exception_rows if row["severity"] == "blocking")
    exception_period_id = next(
        (row["period_id"] for row in exception_rows if row["period_id"]), None
    )
    linked_period_id = finance_period_id or exception_period_id

    document_rows = conn.execute(
        "SELECT status FROM accounting_documents WHERE order_id = %s",
        (order_id,),
    ).fetchall()
    exception_types = {row["exception_type"] for row in exception_rows}
    if "missing_document_reference" in exception_types:
        document_reference_status = "missing"
    elif any(row["status"] == "missing" for row in document_rows):
        document_reference_status = "missing"
    elif any(row["status"] == "review_required" for row in document_rows):
        document_reference_status = "review_required"
    elif document_rows:
        document_reference_status = "recorded"
    else:
        document_reference_status = "not_required"

    if payment_status in {"review_required", "failed", "dispute_open"}:
        payment_reconciliation_status = "review_required"
    elif payment_status in _PAID_ACCOUNTING_STATUSES:
        has_payment_evidence = conn.execute(
            """
            SELECT 1 FROM payments WHERE order_id = %s
            UNION
            SELECT 1 FROM payment_events WHERE order_id = %s
            LIMIT 1
            """,
            (order_id, order_id),
        ).fetchone()
        payment_reconciliation_status = "matched" if has_payment_evidence else "pending"
    elif payment_status in {"pending", "cod_pending", "refund_pending"}:
        payment_reconciliation_status = "pending"
    else:
        payment_reconciliation_status = "not_applicable"

    if payment_method != "card":
        payout_reconciliation_status = "not_applicable"
    elif not stripe_payment_intent_id:
        payout_reconciliation_status = "pending"
    else:
        payout_row = conn.execute(
            """
            SELECT match_status
            FROM stripe_balance_transactions
            WHERE payment_intent_id = %s
            ORDER BY imported_at DESC
            LIMIT 1
            """,
            (stripe_payment_intent_id,),
        ).fetchone()
        if payout_row is None:
            payout_reconciliation_status = "pending"
        elif payout_row["match_status"] in {"matched", "mismatch", "unmatched"}:
            payout_reconciliation_status = payout_row["match_status"]
        else:
            payout_reconciliation_status = "review_required"

    if payment_method != "cod":
        cod_settlement_status = "not_applicable"
    else:
        settlement_row = conn.execute(
            """
            SELECT amount_cents, mismatch_review
            FROM cod_settlements
            WHERE order_id = %s
            """,
            (order_id,),
        ).fetchone()
        if settlement_row is None:
            cod_settlement_status = "pending"
        elif (
            bool(settlement_row["mismatch_review"]) or settlement_row["amount_cents"] != total_cents
        ):
            cod_settlement_status = "mismatch"
        else:
            cod_settlement_status = "settled"

    readiness_status = "blocked" if blocking_exception_count else fallback_readiness_status
    if document_reference_status in {"missing", "review_required"} and readiness_status == "ready":
        readiness_status = "review_required"

    finance_hub_links = None
    if linked_period_id:
        finance_hub_links = {
            "period_id": linked_period_id,
            "period_href": f"/admin/accounting?period={linked_period_id}",
            "exceptions_href": f"/admin/accounting?period={linked_period_id}&tab=exceptions",
            "ledger_href": f"/admin/accounting?period={linked_period_id}&tab=ledgers",
            "documents_href": f"/admin/accounting?period={linked_period_id}&tab=documents",
        }

    return {
        "accounting_readiness_status": readiness_status,
        "document_reference_status": document_reference_status,
        "payment_reconciliation_status": payment_reconciliation_status,
        "payout_reconciliation_status": payout_reconciliation_status,
        "cod_settlement_status": cod_settlement_status,
        "blocking_exception_count": blocking_exception_count,
        "finance_hub_links": finance_hub_links,
    }


def _initial_accounting_classification(
    *,
    invoice_profile: dict | None,
    delivery_country: str,
    seller_country: str = "BG",
) -> str:
    """Assign a conservative initial accounting classification, not tax advice."""
    if invoice_profile and invoice_profile.get("vat_identification_number"):
        return "business_vat_id_provided"
    if delivery_country and delivery_country != seller_country:
        return "cross_border_candidate"
    return "domestic_default"


def _payment_provider_for_method(payment_method: str) -> str:
    if payment_method == "card":
        return "stripe"
    return payment_method


def _ensure_payment_row(
    conn: psycopg.Connection,
    *,
    order_id: str,
    provider: str,
    amount_cents: int,
    provider_status: str,
    now: str,
) -> str:
    row = conn.execute(
        """
        SELECT id
        FROM payments
        WHERE order_id = %s AND provider = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (order_id, provider),
    ).fetchone()
    if row is not None:
        conn.execute(
            "UPDATE payments SET provider_status = %s WHERE id = %s",
            (provider_status, row["id"]),
        )
        return row["id"]

    payment_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO payments (
            id, order_id, provider, amount_cents, currency, provider_status,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, 'EUR', %s, %s, %s)
        """,
        (payment_id, order_id, provider, amount_cents, provider_status, now, now),
    )
    return payment_id


def _append_payment_event(
    conn: psycopg.Connection,
    *,
    order_id: str,
    payment_id: str | None,
    event_type: str,
    provider: str,
    provider_status: str,
    details: dict,
    admin_id: str | None,
    admin_email: str | None,
    admin_note: str,
    request_id: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO payment_events (
            id, order_id, payment_id, event_type, source, provider, provider_status,
            processing_status, details, admin_user_id, admin_email, admin_note, request_id
        ) VALUES (%s, %s, %s, %s, 'admin', %s, %s, 'processed', %s, %s, %s, %s, %s)
        """,
        (
            str(uuid.uuid4()),
            order_id,
            payment_id,
            event_type,
            provider,
            provider_status,
            json.dumps(details, separators=(",", ":")),
            admin_id,
            admin_email,
            admin_note,
            request_id,
        ),
    )


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


class ManualPaymentActionError(OrderServiceError):
    """Raised when a manual payment action is invalid for current state."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


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


class PayOnDeliveryLimitError(OrderServiceError):
    """Raised when a pay-on-delivery order exceeds the configured collection cap."""

    def __init__(self, total_cents: int, max_cents: int) -> None:
        self.total_cents = total_cents
        self.max_cents = max_cents
        super().__init__(f"Pay on delivery is available up to {max_cents} cents")


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


class PaymentReviewRequiredError(OrderServiceError):
    """Raised when fulfillment is blocked by an unresolved payment review."""

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        super().__init__(
            "Order requires admin payment review and customer confirmation before shipping"
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


def _order_weight_grams(conn: psycopg.Connection, order_id: str) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(
            SUM(COALESCE(NULLIF(p.weight_grams, 0), %s) * oi.quantity), %s
        ) AS weight_grams
        FROM order_items oi
        LEFT JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = %s
        """,
        (_DEFAULT_SHIPMENT_WEIGHT_GRAMS, _DEFAULT_SHIPMENT_WEIGHT_GRAMS, order_id),
    ).fetchone()
    return max(1, int(row["weight_grams"] if row else _DEFAULT_SHIPMENT_WEIGHT_GRAMS))


def _speedy_waybill_kwargs(conn: psycopg.Connection, row: dict) -> dict:
    """Build Speedy shipment kwargs from an order row."""
    from app.config import get_settings

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
    weight_grams = _order_weight_grams(conn, row["id"])

    kwargs = {
        "client_id": settings.speedy_client_id,
        "recipient_name": recipient_name,
        "recipient_phone": phone,
        "weight_grams": weight_grams,
        "username": settings.speedy_api_username,
        "password": settings.speedy_api_password.get_secret_value(),
        "order_ref": row["id"],
        "recipient_city": details.get("city"),
        "cod_amount_cents": cod_cents,
    }

    if method == "office":
        kwargs["recipient_office_id"] = details.get("office_id")
        return kwargs

    kwargs.update(
        {
            "recipient_postcode": details.get("postal_code"),
            "recipient_street": details.get("street"),
            "recipient_building": details.get("building"),
        }
    )
    return kwargs


async def _create_speedy_waybill(
    conn: psycopg.Connection, row: dict
) -> tuple[str, str | None]:
    """Create a Speedy waybill from an order row."""
    from app.services import speedy_client

    tracking = await speedy_client.create_shipment(**_speedy_waybill_kwargs(conn, row))
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
    internal_sequence: int | None
    order_number: str | None
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
    courier_provider: str | None
    courier_order_id: str | None
    courier_shipment_number: str | None
    courier_label_url: str | None
    courier_label_created_at: str | None
    courier_sync_status: str | None
    courier_last_error: str | None
    courier_last_synced_at: str | None
    locale: str
    notes: str | None
    payment_method: str
    payment_status: str
    reserved_until: str | None
    paid_at: str | None
    collected_at: str | None
    payment_return_token: str | None
    stripe_checkout_session_id: str | None
    stripe_payment_intent_id: str | None
    invoice_profile: dict | None
    accounting_currency: str
    seller_legal_profile_version_id: int | None
    vat_fiscal_settings_version_id: int | None
    accounting_classification_state: str
    accounting_snapshot: dict | None
    accounting_readiness_status: str
    finance_period_id: str | None
    document_reference_status: str
    payment_reconciliation_status: str
    payout_reconciliation_status: str
    cod_settlement_status: str
    blocking_exception_count: int
    finance_hub_links: dict[str, str | None] | None
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
    conn: psycopg.Connection,
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
    shipping_cents: int = 0,
    shipping_price_source: str = "live",
    shipping_is_fallback: bool = False,
    shipping_quoted_at: str | None = None,
    invoice_profile: InvoiceProfile | None = None,
    pay_on_delivery_max_cents: int | None = None,
) -> OrderData:
    """Convert cart to an order atomically.

    Runs inside a single transaction (``conn.transaction()``) to serialize
    concurrent checkouts — prevents two sessions from decrementing stock past
    zero simultaneously. The CHECK (stock >= 0) constraint is the final guard:
    a race that would drive stock negative raises CheckViolation, mapped to
    InsufficientStockError, and the transaction rolls back.

    Validates stock, creates order with price snapshots, decrements stock,
    and clears cart items — all within an explicit transaction.

    `delivery` is JSON-serialized into `orders.delivery_details` with
    `ensure_ascii=False` so Cyrillic office/city names round-trip readably.
    `shipping_cents` is 0 in this change (real pricing lands in
    `shipping-pricing`); the value is server-enforced.
    """
    # Serialize delivery sub-object (office or door) into JSON blob.
    # ensure_ascii=False preserves Cyrillic — see HANDOFF gotcha #5.
    delivery_details: dict[str, Any] | None
    delivery_courier: str | None
    if delivery.method == "office" and delivery.office is not None:
        office_delivery = delivery.office
        if not delivery_settings_service.is_delivery_method_enabled(
            office_delivery.courier,
            "office",
        ):
            raise DeliveryMethodUnavailableError(office_delivery.courier, "office")
        catalogue_office = delivery_service.get_office(
            office_delivery.courier,
            office_delivery.office_id,
            locale="bg",
        )
        if catalogue_office is None:
            raise InvalidDeliveryOfficeError(office_delivery.office_id, office_delivery.courier)
        if catalogue_office["type"] != office_delivery.office_type:
            raise InvalidDeliveryOfficeError(
                office_delivery.office_id,
                office_delivery.courier,
                reason=f"office_type must be {catalogue_office['type']}",
            )
        delivery_details = office_delivery.model_dump()
        delivery_details["office_name"] = catalogue_office["name"]
        delivery_details["office_type"] = catalogue_office["type"]
        if office_delivery.courier == "econt":
            office_code = catalogue_office.get("code")
            if not office_code:
                raise InvalidDeliveryOfficeError(
                    office_delivery.office_id,
                    office_delivery.courier,
                    reason="office_code required for Econt office delivery",
                )
            delivery_details["office_code"] = office_code
        delivery_courier = office_delivery.courier
    else:
        door_delivery = delivery.door
        if door_delivery is not None and not delivery_settings_service.is_delivery_method_enabled(
            door_delivery.courier,
            "door",
        ):
            raise DeliveryMethodUnavailableError(door_delivery.courier, "door")
        delivery_details = door_delivery.model_dump() if door_delivery is not None else None
        delivery_courier = door_delivery.courier if door_delivery is not None else None

    delivery_details_json = json.dumps(delivery_details, ensure_ascii=False)

    with conn.transaction():
        name_expr = _localized_product_name(locale)
        # 1. Fetch cart items with product info
        cart_rows = conn.execute(
            f"""
            SELECT ci.product_id, ci.quantity, {name_expr}, p.price_cents,
                   p.discount_percent, p.discount_starts_at, p.discount_ends_at,
                   p.stock, p.is_active
            FROM cart_items ci
            JOIN products p ON p.id = ci.product_id
            WHERE ci.session_id = %s
            """,  # noqa: S608 - locale selects a fixed SQL expression above.
            (session_id,),
        ).fetchall()

        if not cart_rows:
            raise EmptyCartError("Cart is empty")

        cart_product_ids = [row["product_id"] for row in cart_rows]
        inventory_modes = _ledger_modes_for_products(conn, cart_product_ids)

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
        now_dt = datetime.now(UTC)
        now = now_dt.strftime(_DT_FMT)
        reserved_until = (
            (now_dt + timedelta(minutes=15)).strftime(_DT_FMT) if payment_method == "card" else None
        )
        internal_sequence = conn.execute(
            "SELECT COALESCE(MAX(internal_sequence), 0) + 1 AS next_seq FROM orders"
        ).fetchone()["next_seq"]
        order_number = _generate_order_number(conn)
        payment_return_token = _generate_payment_return_token(conn)
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

        if (
            payment_method == "cod"
            and pay_on_delivery_max_cents is not None
            and total_cents > pay_on_delivery_max_cents
        ):
            raise PayOnDeliveryLimitError(total_cents, pay_on_delivery_max_cents)

        # Initial payment_status depends on payment method.
        initial_payment_status = "cod_pending" if payment_method == "cod" else "pending"
        invoice_profile_payload = (
            invoice_profile.model_dump(mode="json") if invoice_profile is not None else None
        )
        customer_country = (
            invoice_profile_payload.get("billing_country") if invoice_profile_payload else None
        )
        # Current checkout only collects Bulgarian courier addresses. Keep the
        # explicit country in the accounting snapshot so future cross-border
        # checkout can replace this without changing export contracts.
        delivery_country = "BG"
        seller_profile_version_id = accounting_config_service.current_seller_profile_version_id(
            conn
        )
        vat_fiscal_settings_version_id = (
            accounting_config_service.current_vat_fiscal_settings_version_id(conn)
        )
        accounting_classification_state = _initial_accounting_classification(
            invoice_profile=invoice_profile_payload,
            delivery_country=delivery_country,
        )
        accounting_readiness_status = (
            "ready"
            if seller_profile_version_id is not None and vat_fiscal_settings_version_id is not None
            else "review_required"
        )
        accounting_snapshot = {
            "currency": "EUR",
            "seller_legal_profile_version_id": seller_profile_version_id,
            "vat_fiscal_settings_version_id": vat_fiscal_settings_version_id,
            "payment_method": payment_method,
            "delivery_country": delivery_country,
            "customer_country": customer_country,
            "shipping_cents": shipping_cents,
            "shipping_price_source": shipping_price_source,
            "discounts_captured_in_effective_prices": True,
            "invoice_profile": invoice_profile_payload,
            "items": [
                {
                    "product_id": row["product_id"],
                    "product_name": row["name"],
                    "quantity": row["quantity"],
                    "unit_price_cents": effective_prices[row["product_id"]],
                }
                for row in cart_rows
            ],
        }

        conn.execute(
            """
            INSERT INTO orders (id, session_id, user_id, status, total_cents,
                               internal_sequence, order_number,
                               customer_email, customer_name,
                               shipping_cents, shipping_price_source,
                               shipping_is_fallback, shipping_quoted_at,
                               delivery_method, delivery_courier, delivery_details,
                               locale, notes,
                               payment_method, payment_status, reserved_until,
                               payment_return_token,
                               invoice_profile_json, accounting_currency,
                               seller_legal_profile_version_id,
                               vat_fiscal_settings_version_id,
                               accounting_classification_state,
                               accounting_snapshot_json,
                               accounting_readiness_status,
                               analytics_consent, created_at, updated_at)
            VALUES (
                %s, %s, %s, 'pending', %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s
            )
            """,
            (
                order_id,
                session_id,
                user_id,
                total_cents,
                internal_sequence,
                order_number,
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
                reserved_until,
                payment_return_token,
                json.dumps(invoice_profile_payload, ensure_ascii=False)
                if invoice_profile_payload is not None
                else None,
                "EUR",
                seller_profile_version_id,
                vat_fiscal_settings_version_id,
                accounting_classification_state,
                json.dumps(accounting_snapshot, ensure_ascii=False),
                accounting_readiness_status,
                1 if analytics_consent else 0,
                now,
                now,
            ),
        )

        if payment_method in {"card", "cod"}:
            provider = "stripe" if payment_method == "card" else "cod"
            conn.execute(
                """
                INSERT INTO payments (
                    id, order_id, provider, amount_cents, currency, provider_status,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, 'EUR', %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    order_id,
                    provider,
                    total_cents,
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
                VALUES (%s, %s, %s, %s, %s)
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
                if _is_ledger_managed_mode(inventory_modes.get(row["product_id"], "legacy")):
                    key = _order_item_key(order_id, row["product_id"])
                    _record_finished_good_movement(
                        conn,
                        product_id=row["product_id"],
                        movement_type="sale_issue",
                        quantity_delta=-row["quantity"],
                        source_type="order_item",
                        source_id=key,
                        order_id=order_id,
                        order_item_key=key,
                        actor_user_id=user_id,
                        actor_email=customer_email,
                        notes="Checkout stock issue",
                        review_state="reviewed",
                        occurred_at=now,
                        metadata={"inventory_mode": _LEDGER_MANAGED_MODE},
                    )
                else:
                    conn.execute(
                        "UPDATE products SET stock = stock - %s WHERE id = %s",
                        (row["quantity"], row["product_id"]),
                    )
            except psycopg.errors.CheckViolation as e:
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
        product_ids = cart_product_ids
        placeholders = ",".join("%s" for _ in product_ids)
        conn.execute(
            f"DELETE FROM cart_items WHERE session_id = %s AND product_id IN ({placeholders})",
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
                "VALUES (%s, %s, %s, 'queued')",
                (order_id, customer_event, customer_email),
            )
        # Admin new-order alert rides the same outbox.
        conn.execute(
            "INSERT INTO order_emails (order_id, event, recipient, status) "
            "VALUES (%s, 'admin_new_order', %s, 'queued')",
            (order_id, admin_notification_email or ""),
        )

    return OrderData(
        id=order_id,
        internal_sequence=internal_sequence,
        order_number=order_number,
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
        courier_provider=None,
        courier_order_id=None,
        courier_shipment_number=None,
        courier_label_url=None,
        courier_label_created_at=None,
        courier_sync_status=None,
        courier_last_error=None,
        courier_last_synced_at=None,
        locale=locale,
        notes=notes,
        payment_method=payment_method,
        payment_status=initial_payment_status,
        reserved_until=reserved_until,
        paid_at=None,
        collected_at=None,
        payment_return_token=payment_return_token,
        stripe_checkout_session_id=None,
        stripe_payment_intent_id=None,
        invoice_profile=invoice_profile_payload,
        accounting_currency="EUR",
        seller_legal_profile_version_id=seller_profile_version_id,
        vat_fiscal_settings_version_id=vat_fiscal_settings_version_id,
        accounting_classification_state=accounting_classification_state,
        accounting_snapshot=accounting_snapshot,
        accounting_readiness_status=accounting_readiness_status,
        finance_period_id=None,
        document_reference_status="not_required",
        payment_reconciliation_status=(
            "pending" if initial_payment_status in {"pending", "cod_pending"} else "not_applicable"
        ),
        payout_reconciliation_status="not_applicable",
        cod_settlement_status="pending" if payment_method == "cod" else "not_applicable",
        blocking_exception_count=0,
        finance_hub_links=None,
        analytics_consent=analytics_consent,
        created_at=now,
        updated_at=now,
        items=items,
    )


def _fetch_order_with_items(conn: psycopg.Connection, order_id: str) -> OrderData | None:
    """Fetch an order and its items. Returns None if not found."""
    row = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    if not row:
        return None

    item_rows = conn.execute(
        "SELECT product_id, product_name, price_cents, quantity"
        " FROM order_items WHERE order_id = %s",
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
    delivery_details = _decode_json_dict(
        delivery_details_raw,
        order_id=order_id,
        field="delivery_details",
    )

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
    shipping_quoted_at = (
        _fmt_ts(row["shipping_quoted_at"]) if "shipping_quoted_at" in row_keys else None
    )
    invoice_profile = _decode_json_dict(
        row["invoice_profile_json"] if "invoice_profile_json" in row_keys else None,
        order_id=order_id,
        field="invoice_profile_json",
    )
    accounting_snapshot = _decode_json_dict(
        row["accounting_snapshot_json"] if "accounting_snapshot_json" in row_keys else None,
        order_id=order_id,
        field="accounting_snapshot_json",
    )
    payment_method = row["payment_method"] if "payment_method" in row_keys else "cod"
    payment_status = row["payment_status"] if "payment_status" in row_keys else "cod_pending"
    stripe_payment_intent_id = (
        row["stripe_payment_intent_id"] if "stripe_payment_intent_id" in row_keys else None
    )
    finance_period_id = row["finance_period_id"] if "finance_period_id" in row_keys else None
    accounting_readiness_status = (
        row["accounting_readiness_status"]
        if "accounting_readiness_status" in row_keys and row["accounting_readiness_status"]
        else "unreviewed"
    )
    accounting_admin_fields = _accounting_admin_fields(
        conn,
        order_id=order_id,
        total_cents=total_cents,
        payment_method=payment_method,
        payment_status=payment_status,
        finance_period_id=finance_period_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        fallback_readiness_status=accounting_readiness_status,
    )

    return OrderData(
        id=row["id"],
        internal_sequence=(row["internal_sequence"] if "internal_sequence" in row_keys else None),
        order_number=row["order_number"] if "order_number" in row_keys else None,
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
        courier_provider=row["courier_provider"] if "courier_provider" in row_keys else None,
        courier_order_id=row["courier_order_id"] if "courier_order_id" in row_keys else None,
        courier_shipment_number=(
            row["courier_shipment_number"] if "courier_shipment_number" in row_keys else None
        ),
        courier_label_url=row["courier_label_url"] if "courier_label_url" in row_keys else None,
        courier_label_created_at=(
            _fmt_ts(row["courier_label_created_at"])
            if "courier_label_created_at" in row_keys
            else None
        ),
        courier_sync_status=(
            row["courier_sync_status"] if "courier_sync_status" in row_keys else None
        ),
        courier_last_error=(
            row["courier_last_error"] if "courier_last_error" in row_keys else None
        ),
        courier_last_synced_at=(
            _fmt_ts(row["courier_last_synced_at"])
            if "courier_last_synced_at" in row_keys
            else None
        ),
        locale=(row["locale"] if "locale" in row_keys and row["locale"] else "en"),
        notes=row["notes"],
        payment_method=payment_method,
        payment_status=payment_status,
        reserved_until=(_fmt_ts(row["reserved_until"]) if "reserved_until" in row_keys else None),
        paid_at=_fmt_ts(row["paid_at"]) if "paid_at" in row_keys else None,
        collected_at=_fmt_ts(row["collected_at"]) if "collected_at" in row_keys else None,
        payment_return_token=(
            row["payment_return_token"] if "payment_return_token" in row_keys else None
        ),
        stripe_checkout_session_id=(
            row["stripe_checkout_session_id"] if "stripe_checkout_session_id" in row_keys else None
        ),
        stripe_payment_intent_id=stripe_payment_intent_id,
        invoice_profile=invoice_profile,
        accounting_currency=(
            row["accounting_currency"]
            if "accounting_currency" in row_keys and row["accounting_currency"]
            else "EUR"
        ),
        seller_legal_profile_version_id=(
            row["seller_legal_profile_version_id"]
            if "seller_legal_profile_version_id" in row_keys
            else None
        ),
        vat_fiscal_settings_version_id=(
            row["vat_fiscal_settings_version_id"]
            if "vat_fiscal_settings_version_id" in row_keys
            else None
        ),
        accounting_classification_state=(
            row["accounting_classification_state"]
            if "accounting_classification_state" in row_keys
            and row["accounting_classification_state"]
            else "unreviewed"
        ),
        accounting_snapshot=accounting_snapshot,
        accounting_readiness_status=accounting_admin_fields["accounting_readiness_status"],
        finance_period_id=finance_period_id,
        document_reference_status=accounting_admin_fields["document_reference_status"],
        payment_reconciliation_status=accounting_admin_fields["payment_reconciliation_status"],
        payout_reconciliation_status=accounting_admin_fields["payout_reconciliation_status"],
        cod_settlement_status=accounting_admin_fields["cod_settlement_status"],
        blocking_exception_count=accounting_admin_fields["blocking_exception_count"],
        finance_hub_links=accounting_admin_fields["finance_hub_links"],
        analytics_consent=bool(row["analytics_consent"] if "analytics_consent" in row_keys else 0),
        created_at=_fmt_ts(row["created_at"]),
        updated_at=_fmt_ts(row["updated_at"]),
        items=items,
    )


def get_order_inventory_context(conn: psycopg.Connection, order_id: str) -> dict[str, object]:
    """Return admin-only inventory context for one order."""
    item_rows = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id = %s ORDER BY product_id",
        (order_id,),
    ).fetchall()
    product_ids = [row["product_id"] for row in item_rows]
    inventory_modes = _ledger_modes_for_products(conn, product_ids)
    settings = conn.execute(
        """
        SELECT valuation_enabled, valuation_method, accountant_reviewed
        FROM inventory_settings
        WHERE id = 'default'
        """
    ).fetchone()
    valuation_method = settings["valuation_method"] if settings else "weighted_average"
    official_cogs_required = bool(
        settings and settings["valuation_enabled"] and settings["accountant_reviewed"]
    )

    movement_rows = conn.execute(
        """
        SELECT id, product_id, movement_type, order_item_key, reversal_of_movement_id,
               source_type, source_id, review_state
        FROM inventory_movements
        WHERE order_id = %s
        ORDER BY occurred_at, created_at, id
        """,
        (order_id,),
    ).fetchall()
    movements_by_product: dict[str, list[dict]] = {}
    for movement in movement_rows:
        if movement["product_id"]:
            movements_by_product.setdefault(movement["product_id"], []).append(movement)

    cogs_rows = conn.execute(
        """
        SELECT id, product_id, source_movement_id, source_valuation_layer_id,
               source_finished_batch_id, review_state
        FROM cogs_ledger
        WHERE order_id = %s
          AND review_state != 'reversed'
        ORDER BY created_at, id
        """,
        (order_id,),
    ).fetchall()
    cogs_by_product: dict[str, dict] = {}
    for row in cogs_rows:
        if row["product_id"] and row["product_id"] not in cogs_by_product:
            cogs_by_product[row["product_id"]] = row

    latest_batches: dict[str, dict] = {}
    if product_ids:
        placeholders = ",".join("%s" for _ in product_ids)
        for row in conn.execute(
            f"""
            SELECT pip.product_id, pb.id, pb.batch_number
            FROM product_inventory_profiles pip
            LEFT JOIN production_batches pb ON pb.id = pip.latest_batch_id
            WHERE pip.product_id IN ({placeholders})
            """,  # noqa: S608
            product_ids,
        ).fetchall():
            latest_batches[row["product_id"]] = row

    exception_rows = conn.execute(
        """
        SELECT id, exception_type, severity, target_type, target_id, source_type, source_id
        FROM inventory_exceptions
        WHERE status = 'open'
          AND (
            (target_type = 'order' AND target_id = %s)
            OR (source_type = 'order' AND source_id = %s)
            OR (source_type = 'order_item' AND source_id LIKE %s)
            OR (target_type = 'product' AND target_id IN (
                SELECT product_id FROM order_items WHERE order_id = %s
            ))
          )
        ORDER BY created_at DESC, id DESC
        """,
        (order_id, order_id, f"{order_id}:%", order_id),
    ).fetchall()
    exception_ids_by_product: dict[str, list[str]] = {pid: [] for pid in product_ids}
    order_exception_ids: list[str] = []
    for exc in exception_rows:
        order_exception_ids.append(exc["id"])
        if exc["target_type"] == "product" and exc["target_id"] in exception_ids_by_product:
            exception_ids_by_product[exc["target_id"]].append(exc["id"])
        elif exc["source_type"] == "order_item" and exc["source_id"]:
            product_id = str(exc["source_id"]).split(":", 1)[-1]
            if product_id in exception_ids_by_product:
                exception_ids_by_product[product_id].append(exc["id"])

    item_contexts: dict[str, dict[str, object]] = {}
    missing_movement_count = 0
    missing_cogs_count = 0
    for item in item_rows:
        product_id = item["product_id"]
        inventory_mode = inventory_modes.get(product_id, "legacy")
        ledger_managed = _is_ledger_managed_mode(inventory_mode)
        movements = movements_by_product.get(product_id, [])
        sale_issue = next((m for m in movements if m["movement_type"] == "sale_issue"), None)
        cancellation = next(
            (m for m in movements if m["movement_type"] == "cancellation_reversal"), None
        )
        if not ledger_managed:
            stock_issue_status = "legacy"
        elif cancellation is not None:
            stock_issue_status = "reversed"
        elif sale_issue is not None:
            stock_issue_status = "issued"
        else:
            stock_issue_status = "missing"
            missing_movement_count += 1

        cogs = cogs_by_product.get(product_id)
        if cogs is not None:
            cogs_readiness = cogs["review_state"]
        elif official_cogs_required and ledger_managed:
            cogs_readiness = "missing"
            missing_cogs_count += 1
        elif ledger_managed:
            cogs_readiness = "estimate_only"
        else:
            cogs_readiness = "not_required"

        batch = latest_batches.get(product_id)
        item_contexts[product_id] = {
            "inventory_mode": inventory_mode,
            "ledger_managed": ledger_managed,
            "stock_issue_status": stock_issue_status,
            "inventory_movement_ids": [m["id"] for m in movements],
            "source_movement_id": sale_issue["id"] if sale_issue else None,
            "finished_batch_id": batch["id"] if batch and batch["id"] else None,
            "finished_batch_number": batch["batch_number"] if batch and batch["id"] else None,
            "cogs_row_id": cogs["id"] if cogs else None,
            "cogs_readiness": cogs_readiness,
            "valuation_method": valuation_method if ledger_managed else None,
            "source_valuation_layer_id": cogs["source_valuation_layer_id"] if cogs else None,
            "inventory_exception_ids": exception_ids_by_product.get(product_id, []),
            "inventory_exception_count": len(exception_ids_by_product.get(product_id, [])),
        }

    return {
        "valuation_method": valuation_method,
        "official_cogs_required": official_cogs_required,
        "missing_inventory_movement_count": missing_movement_count,
        "missing_cogs_count": missing_cogs_count,
        "inventory_exception_count": len(order_exception_ids),
        "inventory_exception_ids": order_exception_ids,
        "items": item_contexts,
        "links": {
            "movements_href": f"/admin/inventory/movements?order_id={order_id}",
            "cogs_href": f"/admin/inventory/valuation/cogs?order_id={order_id}",
            "exceptions_href": f"/admin/inventory/valuation/exceptions?order_id={order_id}",
        },
    }


def get_order(
    conn: psycopg.Connection,
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


def get_order_admin(conn: psycopg.Connection, order_id: str) -> OrderData:
    """Fetch order without ownership check (admin auth enforced at route level)."""
    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def list_orders(
    conn: psycopg.Connection,
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
        where_clause = "WHERE user_id = %s"
        params: list = [user_id]
    else:
        where_clause = "WHERE session_id = %s"
        params = [session_id]

    # Total count
    total = conn.execute(
        f"SELECT COUNT(*) AS count FROM orders {where_clause}",  # noqa: S608
        params,
    ).fetchone()["count"]

    # Paginated results
    rows = conn.execute(
        f"SELECT id FROM orders {where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        [*params, limit, offset],
    ).fetchall()

    items: list[OrderData] = []
    for row in rows:
        order = _fetch_order_with_items(conn, row["id"])
        if order is not None:
            items.append(order)

    return OrderListData(items=items, total=total, page=page, limit=limit)


def list_orders_admin(
    conn: psycopg.Connection,
    status: OrderStatus | None = None,
    payment_status: str | None = None,
    payment_method: str | None = None,
    review_filter: str | None = None,
    accounting_filter: str | None = None,
    finance_period_id: str | None = None,
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
        conditions.append("status = %s")
        params.append(status)
    if payment_status is not None:
        conditions.append("payment_status = %s")
        params.append(payment_status)
    if payment_method is not None:
        conditions.append("payment_method = %s")
        params.append(payment_method)
    if finance_period_id is not None:
        conditions.append("finance_period_id = %s")
        params.append(finance_period_id)
    if review_filter == "abandoned_payment":
        conditions.append("payment_method = 'card'")
        conditions.append("payment_status = 'review_required'")
        conditions.append(
            "status NOT IN ('cancelled', 'shipped', 'delivered', 'return_in_transit', 'returned')"
        )
    elif review_filter == "uncollected_refused":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_returns review_return
                WHERE review_return.order_id = orders.id
                  AND review_return.reason IN ('not_picked_up', 'refused_delivery')
                  AND review_return.status NOT IN ('closed', 'rejected')
            )
            """
        )
    elif review_filter == "refund_pending":
        conditions.append(
            """
            (
                payment_status = 'refund_pending'
                OR EXISTS (
                    SELECT 1
                    FROM payment_refunds review_refund
                    WHERE review_refund.order_id = orders.id
                      AND review_refund.status = 'pending'
                )
            )
            """
        )
    elif review_filter == "inspection_pending":
        conditions.append("status = 'returned'")
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_returns review_return
                WHERE review_return.order_id = orders.id
                  AND review_return.restock_decision = 'pending'
                  AND review_return.status NOT IN ('closed', 'rejected')
            )
            """
        )
    elif review_filter == "courier_claim_follow_up":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_returns review_return
                WHERE review_return.order_id = orders.id
                  AND (
                    review_return.courier_claim_status IN ('filed', 'approved')
                    OR (
                        review_return.courier_claim_id IS NOT NULL
                        AND review_return.courier_claim_status NOT IN ('rejected', 'paid')
                    )
                  )
            )
            """
        )
    elif review_filter == "cod_settlement_pending":
        conditions.append("payment_method = 'cod'")
        conditions.append("status = 'delivered'")
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM cod_settlements cs WHERE cs.order_id = orders.id)"
        )

    if accounting_filter == "missing_document_reference":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM finance_exceptions fe
                WHERE fe.target_type = 'order'
                  AND fe.target_id = orders.id
                  AND fe.status = 'open'
                  AND fe.exception_type = 'missing_document_reference'
            )
            """
        )
    elif accounting_filter == "unresolved_exception":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM finance_exceptions fe
                WHERE fe.target_type = 'order'
                  AND fe.target_id = orders.id
                  AND fe.status = 'open'
            )
            """
        )
    elif accounting_filter == "payout_mismatch":
        conditions.append("payment_method = 'card'")
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM stripe_balance_transactions sbt
                WHERE sbt.payment_intent_id = orders.stripe_payment_intent_id
                  AND sbt.match_status = 'mismatch'
            )
            """
        )
    elif accounting_filter == "cod_settlement_pending":
        conditions.append("payment_method = 'cod'")
        conditions.append("status = 'delivered'")
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM cod_settlements cs WHERE cs.order_id = orders.id)"
        )
    elif accounting_filter == "refund_document_missing":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM finance_exceptions fe
                WHERE fe.target_type = 'order'
                  AND fe.target_id = orders.id
                  AND fe.status = 'open'
                  AND fe.exception_type = 'refund_document_missing'
            )
            """
        )
    elif accounting_filter == "vat_review_required":
        conditions.append(
            "accounting_classification_state IN ('cross_border_candidate', 'manual_review_required')"
        )
    elif accounting_filter == "missing_inventory_movement":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_items oi
                JOIN product_inventory_profiles pip
                  ON pip.product_id = oi.product_id
                 AND pip.inventory_mode = 'ledger_managed'
                WHERE oi.order_id = orders.id
                  AND NOT EXISTS (
                    SELECT 1
                    FROM inventory_movements im
                    WHERE im.order_id = oi.order_id
                      AND im.product_id = oi.product_id
                      AND im.order_item_key = oi.order_id || ':' || oi.product_id
                      AND im.movement_type = 'sale_issue'
                  )
            )
            """
        )
    elif accounting_filter == "missing_cogs_row":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM inventory_settings invs
                WHERE invs.id = 'default'
                  AND invs.valuation_enabled = 1
                  AND invs.accountant_reviewed = 1
            )
            """
        )
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_items oi
                JOIN product_inventory_profiles pip
                  ON pip.product_id = oi.product_id
                 AND pip.inventory_mode = 'ledger_managed'
                WHERE oi.order_id = orders.id
                  AND NOT EXISTS (
                    SELECT 1
                    FROM cogs_ledger c
                    WHERE c.order_id = oi.order_id
                      AND c.product_id = oi.product_id
                      AND c.review_state != 'reversed'
                  )
            )
            """
        )
    elif accounting_filter == "valuation_exception":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM inventory_exceptions ie
                WHERE ie.status = 'open'
                  AND (
                    (ie.target_type = 'order' AND ie.target_id = orders.id)
                    OR (ie.source_type = 'order' AND ie.source_id = orders.id)
                    OR EXISTS (
                        SELECT 1
                        FROM order_items oi
                        WHERE oi.order_id = orders.id
                          AND ie.target_type = 'product'
                          AND ie.target_id = oi.product_id
                    )
                  )
            )
            """
        )
    elif accounting_filter == "missing_batch_assignment":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_items oi
                JOIN product_inventory_profiles pip
                  ON pip.product_id = oi.product_id
                 AND pip.inventory_mode = 'ledger_managed'
                WHERE oi.order_id = orders.id
                  AND pip.latest_batch_id IS NULL
            )
            """
        )
    elif accounting_filter == "return_inventory_review_pending":
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM order_returns review_return
                WHERE review_return.order_id = orders.id
                  AND review_return.status NOT IN ('closed', 'rejected')
                  AND review_return.restock_decision = 'pending'
            )
            """
        )

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS count FROM orders {where_clause}",  # noqa: S608
        params,
    ).fetchone()["count"]

    rows = conn.execute(
        f"SELECT id FROM orders {where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        [*params, limit, offset],
    ).fetchall()

    items: list[OrderData] = []
    for row in rows:
        order = _fetch_order_with_items(conn, row["id"])
        if order is not None:
            items.append(order)

    return OrderListData(items=items, total=total, page=page, limit=limit)


def list_payment_events(conn: psycopg.Connection, order_id: str) -> list[dict]:
    """Return safe admin payment timeline rows for an order."""
    rows = conn.execute(
        """
        SELECT id, order_id, payment_id, event_type, source, stripe_event_id,
               stripe_event_type, provider, provider_status, processing_status,
               details, admin_user_id, admin_email, admin_note, request_id, created_at
        FROM payment_events
        WHERE order_id = %s
        ORDER BY created_at ASC, id ASC
        """,
        (order_id,),
    ).fetchall()
    return [dict(row) for row in rows]


async def update_status_async(
    conn: psycopg.Connection,
    order_id: str,
    new_status: OrderStatus,
    tracking_number: str | None = None,
    tracking_carrier: str | None = None,
    tracking_url: str | None = None,
) -> OrderData:
    """Async status update path for transitions that may call courier APIs.

    Speedy waybill creation is network I/O, so the admin route awaits it here
    before calling the synchronous local state transition. The local update still
    re-validates the state transition after the external call.
    """
    if new_status == "shipped" and not tracking_number:
        row = conn.execute(
            "SELECT id, status, payment_method, delivery_method, delivery_courier,"
            " delivery_details, customer_name, total_cents, shipping_cents, payment_status"
            ", tracking_number, tracking_carrier, tracking_url, courier_shipment_number"
            " FROM orders WHERE id = %s",
            (order_id,),
        ).fetchone()
        if not row:
            raise OrderNotFoundError(order_id)

        current_status = row["status"]
        if new_status not in VALID_TRANSITIONS.get(current_status, set()):
            raise InvalidStateTransitionError(order_id, current_status, new_status)
        if row["payment_status"] == "review_required":
            raise PaymentReviewRequiredError(order_id)

        delivery_courier = row["delivery_courier"] if "delivery_courier" in row.keys() else None
        if delivery_courier == "speedy":
            tracking_number, _label_url = await _create_speedy_waybill(conn, row)
            tracking_carrier = tracking_carrier or "speedy"

    return update_status(
        conn=conn,
        order_id=order_id,
        new_status=new_status,
        tracking_number=tracking_number,
        tracking_carrier=tracking_carrier,
        tracking_url=tracking_url,
    )


def update_status(
    conn: psycopg.Connection,
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

    Speedy waybill creation is intentionally not performed here because this
    function is synchronous. Async callers should use update_status_async(),
    which creates the waybill before calling this local state transition.
    """
    row = conn.execute(
        "SELECT id, status, payment_method, delivery_method, delivery_courier,"
        " delivery_details, customer_name, total_cents, shipping_cents, payment_status"
        ", tracking_number, tracking_carrier, tracking_url, courier_shipment_number"
        " FROM orders WHERE id = %s",
        (order_id,),
    ).fetchone()

    if not row:
        raise OrderNotFoundError(order_id)

    current_status = row["status"]
    payment_method = row["payment_method"] if "payment_method" in row.keys() else "cod"
    payment_status = row["payment_status"] if "payment_status" in row.keys() else "cod_pending"

    # Validate transition
    if new_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise InvalidStateTransitionError(order_id, current_status, new_status)

    if new_status == "shipped" and payment_status == "review_required":
        raise PaymentReviewRequiredError(order_id)

    label_url: str | None = None

    if new_status == "shipped":
        delivery_courier = row["delivery_courier"] if "delivery_courier" in row.keys() else None
        if not tracking_number and delivery_courier == "econt":
            existing_tracking = row["tracking_number"] or row["courier_shipment_number"]
            if existing_tracking:
                tracking_number = existing_tracking
                tracking_carrier = tracking_carrier or row["tracking_carrier"] or "econt"
                tracking_url = tracking_url or row["tracking_url"]

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

        courier_provider = tracking_carrier if tracking_carrier in {"speedy", "econt"} else None
        synced_at = datetime.now(UTC).strftime(_DT_FMT)

        conn.execute(
            """
            UPDATE orders
            SET status = %s, tracking_number = %s, tracking_carrier = %s, tracking_url = %s,
                label_url = COALESCE(%s, label_url),
                courier_provider = COALESCE(%s, courier_provider),
                courier_shipment_number = CASE
                    WHEN %s::text IS NOT NULL THEN %s ELSE courier_shipment_number END,
                courier_sync_status = CASE
                    WHEN %s = 'speedy' THEN 'waybill_created' ELSE courier_sync_status END,
                courier_last_error = CASE
                    WHEN %s = 'speedy' THEN NULL ELSE courier_last_error END,
                courier_last_synced_at = CASE
                    WHEN %s = 'speedy' THEN %s ELSE courier_last_synced_at END,
                courier_label_created_at = CASE
                    WHEN %s = 'speedy' THEN COALESCE(courier_label_created_at, %s)
                    ELSE courier_label_created_at END
            WHERE id = %s
            """,
            (
                new_status,
                tracking_number,
                tracking_carrier,
                tracking_url,
                label_url,
                courier_provider,
                courier_provider,
                tracking_number,
                tracking_carrier,
                tracking_carrier,
                tracking_carrier,
                synced_at,
                tracking_carrier,
                synced_at,
                order_id,
            ),
        )
    else:
        conn.execute(
            "UPDATE orders SET status = %s WHERE id = %s",
            (new_status, order_id),
        )

    # COD: auto-advance payment_status to 'paid' on delivery (Decision 2).
    # Cash is collected at delivery by the courier — no manual step needed.
    if new_status == "delivered" and payment_method == "cod":
        now = datetime.now(UTC).strftime(_DT_FMT)
        conn.execute(
            "UPDATE orders "
            "SET payment_status = 'paid', "
            "paid_at = COALESCE(paid_at, %s), "
            "collected_at = COALESCE(collected_at, %s) "
            "WHERE id = %s",
            (now, now, order_id),
        )

    # Restore stock on cancellation
    if new_status == "cancelled":
        item_rows = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = %s",
            (order_id,),
        ).fetchall()
        for item in item_rows:
            product_id = item["product_id"]
            if _is_ledger_managed_mode(_product_inventory_mode(conn, product_id)):
                key = _order_item_key(order_id, product_id)
                issue = _sale_issue_movement(conn, order_id=order_id, product_id=product_id)
                if issue is None:
                    _insert_inventory_exception(
                        conn,
                        exception_type="missing_sale_issue_movement",
                        message="Ledger-managed order cancellation has no original sale issue movement.",
                        target_type="order",
                        target_id=order_id,
                        source_type="order_item",
                        source_id=key,
                    )
                _record_finished_good_movement(
                    conn,
                    product_id=product_id,
                    movement_type="cancellation_reversal",
                    quantity_delta=abs(float(issue["quantity_delta"]))
                    if issue
                    else item["quantity"],
                    source_type="order_cancellation",
                    source_id=order_id,
                    order_id=order_id,
                    order_item_key=key,
                    reason="order_cancelled",
                    notes="Cancellation stock reversal",
                    reversal_of_movement_id=issue["id"] if issue else None,
                    review_state="reviewed" if issue else "unreviewed",
                    metadata={"inventory_mode": _LEDGER_MANAGED_MODE},
                )
            else:
                cursor = conn.execute(
                    "UPDATE products SET stock = stock + %s WHERE id = %s",
                    (item["quantity"], product_id),
                )
                if cursor.rowcount == 0:
                    logger.warning(
                        "Could not restore stock for missing product",
                        product_id=product_id,
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
    conn: psycopg.Connection,
    order_id: str,
) -> OrderData:
    """Mark a bank_transfer order's payment_status as 'paid'.

    Raises WrongPaymentMethodError if the order is not bank_transfer.
    Raises PaymentAlreadyPaidError if already paid.
    Raises OrderNotFoundError if not found.
    """
    row = conn.execute(
        "SELECT id, payment_method, payment_status FROM orders WHERE id = %s",
        (order_id,),
    ).fetchone()
    if not row:
        raise OrderNotFoundError(order_id)
    if row["payment_method"] != "bank_transfer":
        raise WrongPaymentMethodError(order_id, "bank_transfer", row["payment_method"])
    if row["payment_status"] == "paid":
        raise PaymentAlreadyPaidError(order_id)
    if row["payment_status"] != "pending":
        raise ManualPaymentActionError(
            "INVALID_PAYMENT_STATE",
            f"Cannot mark bank transfer paid from {row['payment_status']}",
            409,
        )

    now = datetime.now(UTC).strftime(_DT_FMT)
    conn.execute(
        "UPDATE orders SET payment_status = 'paid', paid_at = COALESCE(paid_at, %s) WHERE id = %s",
        (now, order_id),
    )
    conn.execute(
        "INSERT INTO order_emails (order_id, event, recipient, status)"
        " VALUES (%s, 'placed', (SELECT customer_email FROM orders WHERE id = %s), 'queued')"
        " ON CONFLICT DO NOTHING",
        (order_id, order_id),
    )
    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def apply_manual_payment_action(
    conn: psycopg.Connection,
    order_id: str,
    action: str,
    note: str,
    *,
    callback_outcome: str | None = None,
    admin_id: str | None = None,
    admin_email: str | None = None,
    request_id: str | None = None,
) -> OrderData:
    """Apply a note-required manual payment action using the current status vocabulary."""
    admin_note = note.strip()
    if not admin_note:
        raise ManualPaymentActionError("NOTE_REQUIRED", "A note is required")

    row = conn.execute(
        """
        SELECT id, status, payment_method, payment_status, total_cents, customer_email,
               stripe_checkout_session_id, stripe_payment_intent_id
        FROM orders
        WHERE id = %s
        """,
        (order_id,),
    ).fetchone()
    if not row:
        raise OrderNotFoundError(order_id)

    old_order_status = row["status"]
    old_payment_status = row["payment_status"]
    payment_method = row["payment_method"]
    provider = _payment_provider_for_method(payment_method)
    now = datetime.now(UTC).strftime(_DT_FMT)
    new_payment_status = old_payment_status
    new_payment_method = payment_method
    event_type = f"manual_{action}"
    event_details_extra: dict[str, object] = {}
    queue_placed_email = False

    if action == "mark_paid":
        if old_payment_status == "paid":
            raise PaymentAlreadyPaidError(order_id)
        if old_payment_status == "refunded":
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                "Cannot move a refunded payment to paid",
                409,
            )
        new_payment_status = "paid"
        conn.execute(
            "UPDATE orders SET payment_status = 'paid', paid_at = COALESCE(paid_at, %s) "
            "WHERE id = %s",
            (now, order_id),
        )
        queue_placed_email = payment_method in {"card", "bank_transfer"}
    elif action == "mark_collected":
        if payment_method != "cod":
            raise WrongPaymentMethodError(order_id, "cod", payment_method)
        if old_payment_status == "paid":
            raise PaymentAlreadyPaidError(order_id)
        if old_payment_status == "refunded":
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                "Cannot collect a refunded payment",
                409,
            )
        new_payment_status = "paid"
        conn.execute(
            """
            UPDATE orders
            SET payment_status = 'paid',
                paid_at = COALESCE(paid_at, %s),
                collected_at = COALESCE(collected_at, %s)
            WHERE id = %s
            """,
            (now, now, order_id),
        )
    elif action == "mark_refunded":
        if old_payment_status == "refunded":
            raise ManualPaymentActionError("ALREADY_REFUNDED", "Payment is already refunded", 409)
        if old_payment_status != "paid":
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                "Only paid payments can be marked refunded",
                409,
            )
        new_payment_status = "refunded"
        conn.execute("UPDATE orders SET payment_status = 'refunded' WHERE id = %s", (order_id,))
    elif action == "mark_failed":
        if old_payment_status in {"paid", "refunded"}:
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                f"Cannot move payment from {old_payment_status} to failed",
                409,
            )
        new_payment_status = "failed"
        conn.execute("UPDATE orders SET payment_status = 'failed' WHERE id = %s", (order_id,))
    elif action == "mark_review":
        if old_payment_status in {"paid", "refunded"}:
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                f"Cannot move payment from {old_payment_status} to review_required",
                409,
            )
        new_payment_status = "review_required"
        conn.execute(
            "UPDATE orders SET payment_status = 'review_required' WHERE id = %s",
            (order_id,),
        )
    elif action == "record_callback":
        if payment_method != "card":
            raise ManualPaymentActionError(
                "WRONG_PAYMENT_METHOD",
                "Only abandoned card payments can have callback outcomes recorded",
                422,
            )
        if old_payment_status != "review_required":
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                "Only payments in review_required can have callback outcomes recorded",
                409,
            )
        if callback_outcome not in {"confirmed", "declined", "unreachable", "needs_follow_up"}:
            raise ManualPaymentActionError(
                "CALLBACK_OUTCOME_REQUIRED",
                "A valid callback_outcome is required",
                422,
            )
        new_payment_status = "review_required"
        event_details_extra["callback_outcome"] = callback_outcome
        conn.execute("UPDATE orders SET updated_at = %s WHERE id = %s", (now, order_id))
    elif action == "convert_to_cod":
        if payment_method != "card":
            raise ManualPaymentActionError(
                "WRONG_PAYMENT_METHOD",
                "Only abandoned card payments can be converted to payment on delivery",
                422,
            )
        if old_payment_status != "review_required":
            raise ManualPaymentActionError(
                "INVALID_PAYMENT_STATE",
                "Only payments in review_required can be converted to payment on delivery",
                409,
            )
        if old_order_status not in {"pending", "confirmed"}:
            raise ManualPaymentActionError(
                "INVALID_ORDER_STATE",
                "Only unshipped abandoned card orders can be converted to payment on delivery",
                409,
            )
        if callback_outcome not in (None, "confirmed"):
            raise ManualPaymentActionError(
                "CUSTOMER_CONFIRMATION_REQUIRED",
                "Conversion to payment on delivery requires customer confirmation",
                422,
            )
        original_card_payment = conn.execute(
            """
            SELECT id, stripe_checkout_session_id, stripe_payment_intent_id, provider_status
            FROM payments
            WHERE order_id = %s AND provider = 'stripe'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        new_payment_method = "cod"
        provider = "cod"
        new_payment_status = "cod_pending"
        event_details_extra.update(
            {
                "callback_outcome": "confirmed",
                "converted_to_payment_method": "cod",
                "original_card_payment_id": (
                    original_card_payment["id"] if original_card_payment else None
                ),
                "original_card_provider_status": (
                    original_card_payment["provider_status"] if original_card_payment else None
                ),
                "original_stripe_checkout_session_id": (
                    original_card_payment["stripe_checkout_session_id"]
                    if original_card_payment
                    else row["stripe_checkout_session_id"]
                ),
                "original_stripe_payment_intent_id": (
                    original_card_payment["stripe_payment_intent_id"]
                    if original_card_payment
                    else row["stripe_payment_intent_id"]
                ),
            }
        )
        conn.execute(
            """
            UPDATE orders
            SET payment_method = 'cod', payment_status = 'cod_pending',
                reserved_until = NULL, updated_at = %s
            WHERE id = %s
            """,
            (now, order_id),
        )
    elif action == "cancel":
        if old_order_status == "cancelled":
            raise ManualPaymentActionError("ALREADY_CANCELLED", "Order is already cancelled", 409)
        if "cancelled" not in VALID_TRANSITIONS.get(old_order_status, set()):
            raise InvalidStateTransitionError(order_id, old_order_status, "cancelled")
        update_status(conn, order_id, "cancelled")
        if old_payment_status not in {"paid", "refunded"}:
            new_payment_status = "failed"
            conn.execute("UPDATE orders SET payment_status = 'failed' WHERE id = %s", (order_id,))
    else:
        raise ManualPaymentActionError("INVALID_PAYMENT_ACTION", f"Unknown action: {action}")

    if queue_placed_email:
        conn.execute(
            "INSERT INTO order_emails (order_id, event, recipient, status) "
            "VALUES (%s, 'placed', %s, 'queued') "
            "ON CONFLICT DO NOTHING",
            (order_id, row["customer_email"]),
        )

    payment_id = _ensure_payment_row(
        conn,
        order_id=order_id,
        provider=provider,
        amount_cents=row["total_cents"],
        provider_status=new_payment_status,
        now=now,
    )
    _append_payment_event(
        conn,
        order_id=order_id,
        payment_id=payment_id,
        event_type=event_type,
        provider=provider,
        provider_status=new_payment_status,
        details={
            "action": action,
            "old_order_status": old_order_status,
            "new_order_status": "cancelled" if action == "cancel" else old_order_status,
            "old_payment_method": payment_method,
            "new_payment_method": new_payment_method,
            "old_payment_status": old_payment_status,
            "new_payment_status": new_payment_status,
            "current_vocabulary": True,
            **event_details_extra,
        },
        admin_id=admin_id,
        admin_email=admin_email,
        admin_note=admin_note,
        request_id=request_id,
    )

    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order
