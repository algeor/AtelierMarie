"""Payment service — Stripe Checkout Sessions and webhook event handling.

Stripe SDK is imported inside this module only. No other Layer-1 module imports
stripe directly. All stripe.StripeError exceptions are wrapped into custom
exceptions so the route layer never sees Stripe internals.

Webhook idempotency mirrors the order_emails pattern: INSERT OR IGNORE into
stripe_events on event_id; if rowcount == 0 the event was already processed.
"""

import sqlite3
from datetime import UTC, datetime

import structlog

from app.services.order_service import OrderData, OrderNotFoundError, _fetch_order_with_items

logger = structlog.get_logger(__name__)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PaymentServiceError(Exception):
    """Base class for payment service errors."""


class StripeSessionError(PaymentServiceError):
    """Wraps any stripe.StripeError so routes never see Stripe internals."""


class PaymentAlreadyPaidError(PaymentServiceError):
    """Raised when creating a retry session for an already-paid order."""

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order {order_id} is already paid")


class InvalidRetryStateError(PaymentServiceError):
    """Raised when the order is not in a retryable payment state."""

    def __init__(self, order_id: str, payment_status: str) -> None:
        self.order_id = order_id
        super().__init__(f"Order {order_id} has payment_status='{payment_status}', cannot retry")


# ---------------------------------------------------------------------------
# Stripe Checkout Session helpers
# ---------------------------------------------------------------------------


def create_checkout_session(
    conn: sqlite3.Connection,
    order: OrderData,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: str,
) -> str:
    """Create a Stripe Checkout Session for a card order and store the session ID.

    Returns the Stripe-hosted checkout URL. Wraps all stripe.StripeError into
    StripeSessionError.
    """
    try:
        import stripe  # local import — isolates the Stripe dependency

        stripe.api_key = stripe_secret_key
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": order["total_cents"],
                        "product_data": {"name": f"Order #{order['id'][:8]}"},
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url.replace("{order_id}", order["id"]),
            cancel_url=cancel_url,
            client_reference_id=order["id"],
            customer_email=order["customer_email"],
        )
    except Exception as exc:
        raise StripeSessionError(f"Failed to create Stripe session: {exc}") from exc

    conn.execute(
        "UPDATE orders SET stripe_checkout_session_id = ? WHERE id = ?",
        (session.id, order["id"]),
    )
    return str(session.url)


def create_retry_session(
    conn: sqlite3.Connection,
    order_id: str,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: str,
) -> str:
    """Create a fresh Checkout Session for an existing card order whose previous session expired.

    Raises PaymentAlreadyPaidError if the order is already paid.
    Raises InvalidRetryStateError if payment_status is not 'pending' or 'failed'.
    Raises OrderNotFoundError if the order doesn't exist.
    """
    row = conn.execute(
        "SELECT id, payment_method, payment_status, total_cents, customer_email"
        " FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if not row:
        raise OrderNotFoundError(order_id)

    if row["payment_method"] != "card":
        raise InvalidRetryStateError(order_id, row["payment_status"])
    if row["payment_status"] == "paid":
        raise PaymentAlreadyPaidError(order_id)
    if row["payment_status"] not in ("pending", "failed"):
        raise InvalidRetryStateError(order_id, row["payment_status"])

    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)

    return create_checkout_session(conn, order, success_url, cancel_url, stripe_secret_key)


# ---------------------------------------------------------------------------
# Webhook event handlers
# ---------------------------------------------------------------------------


def handle_payment_succeeded(
    conn: sqlite3.Connection,
    event_id: str,
    order_id: str,
    payment_intent_id: str | None,
    now: str,
    stripe_session_id: str | None = None,
) -> bool:
    """Handle checkout.session.completed: set payment_status='paid', queue 'placed' email.

    Uses stripe_events dedup (INSERT OR IGNORE). Returns True if processed,
    False if already seen (idempotent).
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, order_id, event_type, received_at)"
            " VALUES (?, ?, 'checkout.session.completed', ?)",
            (event_id, order_id, now),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            return False

        order_row = conn.execute(
            """
            SELECT customer_email, status, payment_method, payment_status,
                   stripe_checkout_session_id
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        can_mark_paid = False
        if order_row:
            stored_session_id = order_row["stripe_checkout_session_id"]
            session_matches = not stored_session_id or stripe_session_id == stored_session_id
            can_mark_paid = (
                order_row["payment_method"] == "card"
                and order_row["status"] != "cancelled"
                and order_row["payment_status"] in ("pending", "failed")
                and session_matches
            )

        if can_mark_paid:
            conn.execute(
                "UPDATE orders SET payment_status = 'paid', stripe_payment_intent_id = ? "
                "WHERE id = ?",
                (payment_intent_id, order_id),
            )
            # Queue 'placed' email now that payment is confirmed.
            conn.execute(
                "INSERT INTO order_emails (order_id, event, recipient, status)"
                " VALUES (?, 'placed', ?, 'queued')",
                (order_id, order_row["customer_email"]),
            )
        else:
            logger.warning(
                "stripe_payment_succeeded_ignored",
                order_id=order_id,
                event_id=event_id,
                stripe_session_id=stripe_session_id,
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info("stripe_payment_succeeded", order_id=order_id, event_id=event_id)
    return True


def handle_session_expired(
    conn: sqlite3.Connection,
    event_id: str,
    order_id: str,
    stripe_session_id: str,
    now: str,
) -> bool:
    """Handle checkout.session.expired: set payment_status='failed'.

    Only updates when payment_status is still 'pending' AND the current
    stripe_checkout_session_id matches — guards against late-arriving expired
    events for superseded sessions after a successful retry.

    Uses stripe_events dedup. Returns True if processed, False if already seen.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, order_id, event_type, received_at)"
            " VALUES (?, ?, 'checkout.session.expired', ?)",
            (event_id, order_id, now),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            return False

        conn.execute(
            "UPDATE orders SET payment_status = 'failed'"
            " WHERE id = ? AND payment_status = 'pending'"
            " AND stripe_checkout_session_id = ?",
            (order_id, stripe_session_id),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info("stripe_session_expired", order_id=order_id, event_id=event_id)
    return True


def _now_str() -> str:
    return datetime.now(UTC).strftime(_DT_FMT)
