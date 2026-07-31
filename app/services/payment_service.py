"""Payment service — Stripe Checkout Sessions and webhook event handling.

Stripe SDK is imported inside this module only. No other Layer-1 module imports
stripe directly. All stripe.StripeError exceptions are wrapped into custom
exceptions so the route layer never sees Stripe internals.

Webhook idempotency mirrors the order_emails pattern: INSERT OR IGNORE into
stripe_events on event_id; if rowcount == 0 the event was already processed.
"""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog

from app.services.admin_alert_service import create_admin_alert
from app.services.order_service import OrderData, OrderNotFoundError, _fetch_order_with_items

logger = structlog.get_logger(__name__)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _format_stripe_return_url(template: str, order: OrderData) -> str:
    """Fill safe order placeholders and ensure return-token query params exist."""
    token = order["payment_return_token"] or ""
    url = (
        template.replace("{order_id}", order["id"])
        .replace("{order_number}", order["order_number"] or "")
        .replace("{payment_return_token}", token)
    )
    if not url:
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("order_id", order["id"])
    if token and "token" not in query and "payment_return_token" not in query:
        query["token"] = token
    return urlunparse(parsed._replace(query=urlencode(query)))


def _upsert_stripe_payment_row(
    conn: sqlite3.Connection,
    order: OrderData,
    *,
    stripe_checkout_session_id: str | None,
    stripe_payment_intent_id: str | None = None,
    provider_status: str | None = None,
    checkout_url: str | None = None,
) -> None:
    row = conn.execute(
        """
        SELECT id
        FROM payments
        WHERE order_id = ? AND provider = 'stripe'
        ORDER BY created_at DESC
        """,
        (order["id"],),
    ).fetchone()
    details = (
        json.dumps({"checkout_url": checkout_url}, separators=(",", ":"))
        if checkout_url
        else None
    )
    now = _now_str()

    if row is None:
        conn.execute(
            """
            INSERT INTO payments (
                id, order_id, provider, amount_cents, currency,
                stripe_checkout_session_id, stripe_payment_intent_id,
                provider_status, provider_details, created_at, updated_at
            ) VALUES (?, ?, 'stripe', ?, 'EUR', ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                order["id"],
                order["total_cents"],
                stripe_checkout_session_id,
                stripe_payment_intent_id,
                provider_status,
                details,
                now,
                now,
            ),
        )
        return

    conn.execute(
        """
        UPDATE payments
        SET stripe_checkout_session_id = COALESCE(?, stripe_checkout_session_id),
            stripe_payment_intent_id = COALESCE(?, stripe_payment_intent_id),
            provider_status = COALESCE(?, provider_status),
            provider_details = COALESCE(?, provider_details)
        WHERE id = ?
        """,
        (stripe_checkout_session_id, stripe_payment_intent_id, provider_status, details, row["id"]),
    )


def _stored_checkout_url(conn: sqlite3.Connection, order_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT provider_details
        FROM payments
        WHERE order_id = ? AND provider = 'stripe'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (order_id,),
    ).fetchone()
    if row is None or not row["provider_details"]:
        return None
    try:
        details = json.loads(row["provider_details"])
    except json.JSONDecodeError:
        return None
    url = details.get("checkout_url")
    return url if isinstance(url, str) and url else None


def _reservation_is_active(reserved_until: str | None) -> bool:
    if not reserved_until:
        return False
    try:
        expires_at = datetime.strptime(reserved_until, _DT_FMT).replace(tzinfo=UTC)
    except ValueError:
        return False
    return expires_at > datetime.now(UTC)


def _payment_id_for_order(
    conn: sqlite3.Connection, order_id: str, provider: str = "stripe"
) -> str | None:
    row = conn.execute(
        """
        SELECT id
        FROM payments
        WHERE order_id = ? AND provider = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (order_id, provider),
    ).fetchone()
    return row["id"] if row else None


def _order_id_for_payment_intent(
    conn: sqlite3.Connection, payment_intent_id: str | None
) -> str | None:
    if not payment_intent_id:
        return None

    row = conn.execute(
        "SELECT id FROM orders WHERE stripe_payment_intent_id = ? LIMIT 1",
        (payment_intent_id,),
    ).fetchone()
    if row:
        return row["id"]

    row = conn.execute(
        """
        SELECT order_id
        FROM payments
        WHERE stripe_payment_intent_id = ? AND provider = 'stripe'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (payment_intent_id,),
    ).fetchone()
    return row["order_id"] if row else None


def _append_stripe_payment_event(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    event_type: str,
    order_id: str | None,
    payment_id: str | None,
    provider_status: str | None,
    processing_status: str = "processed",
    details: dict | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO payment_events (
            id, order_id, payment_id, event_type, source, stripe_event_id,
            stripe_event_type, provider, provider_status, processing_status, details
        ) VALUES (?, ?, ?, ?, 'stripe', ?, ?, 'stripe', ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            order_id,
            payment_id,
            event_type,
            event_id,
            event_type,
            provider_status,
            processing_status,
            json.dumps(details or {}, separators=(",", ":")),
        ),
    )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PaymentServiceError(Exception):
    """Base class for payment service errors."""


class StripeSessionError(PaymentServiceError):
    """Wraps any stripe.StripeError so routes never see Stripe internals."""


class StripeWebhookVerificationError(PaymentServiceError):
    """Raised when Stripe webhook signature verification fails."""


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


class InvalidRetryTokenError(PaymentServiceError):
    """Raised when a retry request does not present the order return token."""


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
                        "product_data": {
                            "name": f"Order {order['order_number'] or order['id'][:8]}"
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=_format_stripe_return_url(success_url, order),
            cancel_url=_format_stripe_return_url(cancel_url, order),
            client_reference_id=order["id"],
            customer_email=order["customer_email"],
            metadata={
                "order_id": order["id"],
                "order_number": order["order_number"] or "",
            },
        )
    except Exception as exc:
        raise StripeSessionError(f"Failed to create Stripe session: {exc}") from exc

    conn.execute(
        "UPDATE orders SET stripe_checkout_session_id = ? WHERE id = ?",
        (session.id, order["id"]),
    )
    _upsert_stripe_payment_row(
        conn,
        order,
        stripe_checkout_session_id=str(session.id),
        stripe_payment_intent_id=getattr(session, "payment_intent", None),
        provider_status=getattr(session, "status", None) or "open",
        checkout_url=str(session.url),
    )
    return str(session.url)


def create_retry_session(
    conn: sqlite3.Connection,
    order_id: str,
    payment_return_token: str,
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
        """
        SELECT id, payment_method, payment_status, status, payment_return_token, reserved_until
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    ).fetchone()
    if not row:
        raise OrderNotFoundError(order_id)

    if not payment_return_token or payment_return_token != row["payment_return_token"]:
        raise InvalidRetryTokenError(order_id)

    if row["payment_method"] != "card":
        raise InvalidRetryStateError(order_id, row["payment_status"])
    if row["payment_status"] == "paid":
        raise PaymentAlreadyPaidError(order_id)
    if row["status"] == "cancelled":
        raise InvalidRetryStateError(order_id, row["payment_status"])
    if row["payment_status"] not in ("pending", "failed"):
        raise InvalidRetryStateError(order_id, row["payment_status"])
    if not _reservation_is_active(row["reserved_until"]):
        raise InvalidRetryStateError(order_id, row["payment_status"])

    order = _fetch_order_with_items(conn, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)

    if order["payment_status"] == "pending":
        existing_url = _stored_checkout_url(conn, order_id)
        if existing_url:
            return existing_url

    return create_checkout_session(conn, order, success_url, cancel_url, stripe_secret_key)


def construct_stripe_webhook_event(
    raw_body: bytes,
    sig_header: str,
    webhook_secret: str,
    stripe_secret_key: str,
) -> object:
    """Verify and construct a Stripe webhook event behind the service boundary."""
    try:
        import stripe  # local import — isolates the Stripe dependency

        stripe.api_key = stripe_secret_key
        return stripe.Webhook.construct_event(raw_body, sig_header, webhook_secret)
    except Exception as exc:
        raise StripeWebhookVerificationError("Stripe signature rejected") from exc


def expire_checkout_session(stripe_checkout_session_id: str | None, stripe_secret_key: str) -> bool:
    """Attempt to expire an active Stripe Checkout Session."""
    if not stripe_checkout_session_id or not stripe_secret_key:
        return False
    try:
        import stripe  # local import — isolates the Stripe dependency

        stripe.api_key = stripe_secret_key
        stripe.checkout.Session.expire(stripe_checkout_session_id)
        return True
    except Exception as exc:
        logger.warning(
            "stripe_checkout_session_expire_failed",
            stripe_checkout_session_id=stripe_checkout_session_id,
            error_type=type(exc).__name__,
        )
        return False


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
    admin_notification_email: str | None = None,
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
                   order_number, stripe_checkout_session_id, reserved_until
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        can_mark_paid = False
        processing_status = "ignored"
        provider_status = "ignored"
        details = {
            "checkout_session_id": stripe_session_id,
            "payment_intent_id": payment_intent_id,
        }
        if order_row:
            stored_session_id = order_row["stripe_checkout_session_id"]
            session_matches = not stored_session_id or stripe_session_id == stored_session_id
            reservation_active = _reservation_is_active(order_row["reserved_until"])
            requires_review = (
                order_row["payment_method"] == "card"
                and order_row["payment_status"] in ("pending", "failed")
                and session_matches
                and not reservation_active
            )
            can_mark_paid = (
                order_row["payment_method"] == "card"
                and order_row["status"] != "cancelled"
                and order_row["payment_status"] in ("pending", "failed")
                and session_matches
                and reservation_active
            )
            if requires_review:
                details["ignored_reason"] = "reservation_expired"
                details["requires_admin_review"] = True
            elif not session_matches:
                details["ignored_reason"] = "session_mismatch"
            elif order_row["payment_method"] != "card":
                details["ignored_reason"] = "non_card_order"
            elif order_row["status"] == "cancelled":
                details["ignored_reason"] = "order_cancelled"
            elif order_row["payment_status"] not in ("pending", "failed"):
                details["ignored_reason"] = "payment_status_not_retryable"
            elif not reservation_active:
                details["ignored_reason"] = "reservation_expired"
        else:
            details["ignored_reason"] = "order_not_found"

        if can_mark_paid:
            conn.execute(
                "UPDATE orders SET payment_status = 'paid', paid_at = COALESCE(paid_at, ?), "
                "stripe_payment_intent_id = ? "
                "WHERE id = ?",
                (now, payment_intent_id, order_id),
            )
            # Queue 'placed' email now that payment is confirmed.
            conn.execute(
                "INSERT INTO order_emails (order_id, event, recipient, status)"
                " VALUES (?, 'placed', ?, 'queued')",
                (order_id, order_row["customer_email"]),
            )
            payment_id = _payment_id_for_order(conn, order_id)
            if payment_id:
                conn.execute(
                    """
                    UPDATE payments
                    SET stripe_payment_intent_id = COALESCE(?, stripe_payment_intent_id),
                        provider_status = 'paid',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (payment_intent_id, now, payment_id),
                )
            processing_status = "processed"
            provider_status = "paid"
        else:
            logger.warning(
                "stripe_payment_succeeded_ignored",
                order_id=order_id,
                event_id=event_id,
                stripe_session_id=stripe_session_id,
            )
            payment_id = _payment_id_for_order(conn, order_id) if order_row else None
            if order_row and details.get("requires_admin_review"):
                conn.execute(
                    "UPDATE orders SET payment_status = 'failed' "
                    "WHERE id = ? AND payment_status IN ('pending', 'failed')",
                    (order_id,),
                )
                if payment_id:
                    conn.execute(
                        """
                        UPDATE payments
                        SET stripe_payment_intent_id = COALESCE(?, stripe_payment_intent_id),
                            provider_status = 'failed',
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (payment_intent_id, now, payment_id),
                    )
                processing_status = "requires_review"
                provider_status = "failed"
                logger.warning(
                    "stripe_payment_success_requires_review",
                    order_id=order_id,
                    event_id=event_id,
                    stripe_session_id=stripe_session_id,
                    payment_intent_id=payment_intent_id,
                )
                display_order = order_row["order_number"] or order_id[:8]
                alert_details = {
                    "stripe_event_id": event_id,
                    "stripe_event_type": "checkout.session.completed",
                    "checkout_session_id": stripe_session_id,
                    "payment_intent_id": payment_intent_id,
                    "reason": details.get("ignored_reason"),
                    "processing_status": "requires_review",
                }
                create_admin_alert(
                    conn,
                    alert_type="payment_requires_review",
                    order_id=order_id,
                    source="stripe",
                    severity="warning",
                    title=f"Payment review required for {display_order}",
                    message="Late Stripe success arrived after the local reservation expired.",
                    details=alert_details,
                )
                conn.execute(
                    "INSERT INTO order_emails (order_id, event, recipient, status)"
                    " VALUES (?, 'admin_payment_review_required', ?, 'queued')",
                    (order_id, admin_notification_email or ""),
                )

        _append_stripe_payment_event(
            conn,
            event_id=event_id,
            event_type="checkout.session.completed",
            order_id=order_id if order_row else None,
            payment_id=payment_id,
            provider_status=provider_status,
            processing_status=processing_status,
            details=details,
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

        order_row = conn.execute(
            "SELECT id FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        payment_id = _payment_id_for_order(conn, order_id) if order_row else None
        cur = conn.execute(
            "UPDATE orders SET payment_status = 'failed'"
            " WHERE id = ? AND payment_status = 'pending'"
            " AND stripe_checkout_session_id = ?",
            (order_id, stripe_session_id),
        )
        if cur.rowcount and payment_id:
            conn.execute(
                """
                UPDATE payments
                SET provider_status = 'failed', updated_at = ?
                WHERE id = ?
                """,
                (now, payment_id),
            )
        _append_stripe_payment_event(
            conn,
            event_id=event_id,
            event_type="checkout.session.expired",
            order_id=order_id if order_row else None,
            payment_id=payment_id,
            provider_status="failed" if cur.rowcount else "ignored",
            processing_status="processed" if cur.rowcount else "ignored",
            details={
                "checkout_session_id": stripe_session_id,
                "updated_order": bool(cur.rowcount),
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info("stripe_session_expired", order_id=order_id, event_id=event_id)
    return True


def handle_payment_failed(
    conn: sqlite3.Connection,
    event_id: str,
    order_id: str | None,
    payment_intent_id: str | None,
    now: str,
    *,
    error_code: str | None = None,
    event_created: int | None = None,
    livemode: bool | None = None,
) -> bool:
    """Handle payment_intent.payment_failed as audit-only for Checkout reservations."""
    resolved_order_id = order_id or None
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, order_id, event_type, received_at)"
            " VALUES (?, ?, 'payment_intent.payment_failed', ?)",
            (event_id, resolved_order_id, now),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            return False

        if not resolved_order_id:
            resolved_order_id = _order_id_for_payment_intent(conn, payment_intent_id)
            if resolved_order_id:
                conn.execute(
                    "UPDATE stripe_events SET order_id = ? WHERE event_id = ?",
                    (resolved_order_id, event_id),
                )

        payment_id = _payment_id_for_order(conn, resolved_order_id) if resolved_order_id else None
        if payment_id:
            conn.execute(
                """
                UPDATE payments
                SET stripe_payment_intent_id = COALESCE(?, stripe_payment_intent_id),
                    provider_status = 'failed',
                    updated_at = ?
                WHERE id = ?
                """,
                (payment_intent_id, now, payment_id),
            )

        _append_stripe_payment_event(
            conn,
            event_id=event_id,
            event_type="payment_intent.payment_failed",
            order_id=resolved_order_id,
            payment_id=payment_id,
            provider_status="failed",
            processing_status="processed" if resolved_order_id else "unmatched",
            details={
                "payment_intent_id": payment_intent_id,
                "error_code": error_code,
                "event_created": event_created,
                "livemode": livemode,
                "order_status_unchanged": True,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info(
        "stripe_payment_failed",
        order_id=resolved_order_id,
        event_id=event_id,
        payment_intent_id=payment_intent_id,
    )
    return True


def handle_charge_refunded(
    conn: sqlite3.Connection,
    event_id: str,
    order_id: str | None,
    charge_id: str | None,
    payment_intent_id: str | None,
    now: str,
    *,
    amount_refunded: int | None = None,
    event_created: int | None = None,
    livemode: bool | None = None,
) -> bool:
    """Handle charge.refunded as audit-only; order/payment status is unchanged in MVP."""
    resolved_order_id = order_id or None
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, order_id, event_type, received_at)"
            " VALUES (?, ?, 'charge.refunded', ?)",
            (event_id, resolved_order_id, now),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            return False

        if not resolved_order_id:
            resolved_order_id = _order_id_for_payment_intent(conn, payment_intent_id)
            if resolved_order_id:
                conn.execute(
                    "UPDATE stripe_events SET order_id = ? WHERE event_id = ?",
                    (resolved_order_id, event_id),
                )

        payment_id = _payment_id_for_order(conn, resolved_order_id) if resolved_order_id else None
        _append_stripe_payment_event(
            conn,
            event_id=event_id,
            event_type="charge.refunded",
            order_id=resolved_order_id,
            payment_id=payment_id,
            provider_status="refunded",
            processing_status="processed" if resolved_order_id else "unmatched",
            details={
                "charge_id": charge_id,
                "payment_intent_id": payment_intent_id,
                "amount_refunded": amount_refunded,
                "event_created": event_created,
                "livemode": livemode,
                "audit_only": True,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info(
        "stripe_charge_refunded_audit",
        order_id=resolved_order_id,
        event_id=event_id,
        charge_id=charge_id,
    )
    return True


def _now_str() -> str:
    return datetime.now(UTC).strftime(_DT_FMT)
