"""Payment service — Stripe Checkout Sessions and webhook event handling.

Stripe SDK is imported inside this module only. No other Layer-1 module imports
stripe directly. All stripe.StripeError exceptions are wrapped into custom
exceptions so the route layer never sees Stripe internals.

Webhook idempotency mirrors the order_emails pattern: INSERT OR IGNORE into
stripe_events on event_id; if rowcount == 0 the event was already processed.
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any
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
        json.dumps({"checkout_url": checkout_url}, separators=(",", ":")) if checkout_url else None
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


class StripeRefundActionError(PaymentServiceError):
    """Raised when an admin Stripe refund action is invalid or provider creation fails."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Stripe Checkout Session helpers
# ---------------------------------------------------------------------------


def _create_stripe_checkout_session(
    order: OrderData,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: str,
) -> object:
    """Create the provider-side Stripe Checkout Session.

    This helper intentionally does no SQLite work so async callers can run only
    the blocking provider call in a worker thread and persist on the owning DB
    thread afterward.
    """
    import stripe  # local import — isolates the Stripe dependency

    stripe.api_key = stripe_secret_key
    return stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": order["total_cents"],
                    "product_data": {"name": f"Order {order['order_number'] or order['id'][:8]}"},
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


def _persist_checkout_session(
    conn: sqlite3.Connection,
    order: OrderData,
    session: object,
) -> str:
    conn.execute(
        "UPDATE orders SET stripe_checkout_session_id = ? WHERE id = ?",
        (getattr(session, "id"), order["id"]),
    )
    _upsert_stripe_payment_row(
        conn,
        order,
        stripe_checkout_session_id=str(getattr(session, "id")),
        stripe_payment_intent_id=getattr(session, "payment_intent", None),
        provider_status=getattr(session, "status", None) or "open",
        checkout_url=str(getattr(session, "url")),
    )
    return str(getattr(session, "url"))


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
        session = _create_stripe_checkout_session(
            order,
            success_url,
            cancel_url,
            stripe_secret_key,
        )
    except Exception as exc:
        raise StripeSessionError(f"Failed to create Stripe session: {exc}") from exc

    return _persist_checkout_session(conn, order, session)


async def create_checkout_session_async(
    conn: sqlite3.Connection,
    order: OrderData,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: str,
) -> str:
    """Async route-friendly Checkout Session creation.

    Only the blocking Stripe SDK call is offloaded. SQLite writes stay on the
    connection owner thread because sqlite3 connections are thread-bound.
    """
    try:
        session = await asyncio.to_thread(
            _create_stripe_checkout_session,
            order,
            success_url,
            cancel_url,
            stripe_secret_key,
        )
    except Exception as exc:
        raise StripeSessionError(f"Failed to create Stripe session: {exc}") from exc

    return _persist_checkout_session(conn, order, session)


def create_retry_checkout_session(
    conn: sqlite3.Connection,
    order: OrderData,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: str,
) -> str:
    """Create a retry Checkout Session and mark failed orders pending again."""
    url = create_checkout_session(conn, order, success_url, cancel_url, stripe_secret_key)
    if order["payment_status"] == "failed":
        conn.execute(
            "UPDATE orders SET payment_status = 'pending', updated_at = ? WHERE id = ?",
            (_now_str(), order["id"]),
        )
        order["payment_status"] = "pending"
    return url


async def create_retry_checkout_session_async(
    conn: sqlite3.Connection,
    order: OrderData,
    success_url: str,
    cancel_url: str,
    stripe_secret_key: str,
) -> str:
    """Async version of create_retry_checkout_session for FastAPI routes."""
    url = await create_checkout_session_async(
        conn, order, success_url, cancel_url, stripe_secret_key
    )
    if order["payment_status"] == "failed":
        conn.execute(
            "UPDATE orders SET payment_status = 'pending', updated_at = ? WHERE id = ?",
            (_now_str(), order["id"]),
        )
        order["payment_status"] = "pending"
    return url


def _stripe_object_value(obj: object, key: str) -> object | None:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _stripe_refund_create(
    *,
    payment_intent_id: str,
    amount_cents: int,
    reason: str | None,
    idempotency_key: str,
    stripe_secret_key: str,
) -> object:
    import stripe  # local import keeps Stripe isolated to the payment layer

    stripe.api_key = stripe_secret_key
    if reason:
        return stripe.Refund.create(
            payment_intent=payment_intent_id,
            amount=amount_cents,
            metadata={"admin_reason": reason},
            idempotency_key=idempotency_key,
        )
    return stripe.Refund.create(
        payment_intent=payment_intent_id,
        amount=amount_cents,
        idempotency_key=idempotency_key,
    )


def _refund_row(conn: sqlite3.Connection, refund_id: str) -> dict:
    row = conn.execute("SELECT * FROM payment_refunds WHERE id = ?", (refund_id,)).fetchone()
    if row is None:
        raise StripeRefundActionError("REFUND_NOT_FOUND", "Refund record was not found", 500)
    return dict(row)


def _refunded_or_pending_total(conn: sqlite3.Connection, order_id: str) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_cents), 0) AS total
        FROM payment_refunds
        WHERE order_id = ? AND provider = 'stripe' AND status IN ('pending', 'succeeded')
        """,
        (order_id,),
    ).fetchone()
    return int(row["total"] if row else 0)


def _append_admin_refund_event(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    payment_id: str | None,
    event_type: str,
    provider_status: str,
    details: dict,
    admin_id: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO payment_events (
            id, order_id, payment_id, event_type, source, provider, provider_status,
            processing_status, details, admin_user_id
        ) VALUES (?, ?, ?, ?, 'admin', 'stripe', ?, 'processed', ?, ?)
        """,
        (
            str(uuid.uuid4()),
            order_id,
            payment_id,
            event_type,
            provider_status,
            json.dumps(details, separators=(",", ":")),
            admin_id,
        ),
    )


async def create_stripe_refund_async(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    amount_cents: int | None,
    reason: str | None,
    idempotency_key: str,
    admin_id: str | None = None,
    stripe_secret_key: str | None = None,
) -> dict:
    """Create a bounded Stripe refund and store a pending local refund record."""
    if not stripe_secret_key:
        raise StripeRefundActionError("STRIPE_NOT_CONFIGURED", "Stripe is not configured", 409)

    clean_key = idempotency_key.strip()
    if not clean_key:
        raise StripeRefundActionError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency key is required")

    now = _now_str()
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            """
            SELECT * FROM payment_refunds
            WHERE provider = 'stripe' AND idempotency_key = ?
            LIMIT 1
            """,
            (clean_key,),
        ).fetchone()
        if existing is not None:
            conn.execute("COMMIT")
            return dict(existing)

        order = conn.execute(
            """
            SELECT id, total_cents, payment_method, payment_status, stripe_payment_intent_id
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        if order is None:
            raise OrderNotFoundError(order_id)
        if order["payment_method"] != "card":
            raise StripeRefundActionError(
                "WRONG_PAYMENT_METHOD",
                "Stripe refunds can only be issued for card orders",
                422,
            )
        if order["payment_status"] not in {"paid", "partially_refunded", "refund_pending"}:
            raise StripeRefundActionError(
                "INVALID_PAYMENT_STATE",
                "Only paid card orders can be refunded through Stripe",
                409,
            )

        payment = conn.execute(
            """
            SELECT id, stripe_payment_intent_id
            FROM payments
            WHERE order_id = ? AND provider = 'stripe'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        payment_id = payment["id"] if payment else None
        payment_intent_id = (payment["stripe_payment_intent_id"] if payment else None) or order[
            "stripe_payment_intent_id"
        ]
        if not payment_intent_id:
            raise StripeRefundActionError(
                "MISSING_STRIPE_PAYMENT_INTENT",
                "Order does not have a Stripe PaymentIntent to refund",
                409,
            )

        already_refunding = _refunded_or_pending_total(conn, order_id)
        remaining = int(order["total_cents"]) - already_refunding
        refund_amount = remaining if amount_cents is None else amount_cents
        if refund_amount < 1:
            raise StripeRefundActionError("INVALID_REFUND_AMOUNT", "Refund amount must be positive")
        if refund_amount > remaining:
            raise StripeRefundActionError(
                "REFUND_AMOUNT_EXCEEDS_PAID",
                "Refund amount exceeds the remaining refundable amount",
                409,
            )

        refund_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO payment_refunds (
                id, order_id, payment_id, provider, amount_cents, status, reason,
                idempotency_key, created_by_admin_id, created_at
            ) VALUES (?, ?, ?, 'stripe', ?, 'pending', ?, ?, ?, ?)
            """,
            (refund_id, order_id, payment_id, refund_amount, reason, clean_key, admin_id, now),
        )
        conn.execute(
            "UPDATE orders SET payment_status = 'refund_pending', updated_at = ? WHERE id = ?",
            (now, order_id),
        )
        if payment_id:
            conn.execute(
                "UPDATE payments SET provider_status = 'refund_pending', updated_at = ? WHERE id = ?",
                (now, payment_id),
            )
        _append_admin_refund_event(
            conn,
            order_id=order_id,
            payment_id=payment_id,
            event_type="refund_requested",
            provider_status="refund_pending",
            details={
                "amount_cents": refund_amount,
                "idempotency_key": clean_key,
                "remaining_refundable_before_refund": remaining,
            },
            admin_id=admin_id,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    try:
        stripe_refund = await asyncio.to_thread(
            _stripe_refund_create,
            payment_intent_id=payment_intent_id,
            amount_cents=refund_amount,
            reason=reason,
            idempotency_key=clean_key,
            stripe_secret_key=stripe_secret_key,
        )
    except Exception as exc:
        failure_reason = str(exc)
        failed_at = _now_str()
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """
                UPDATE payment_refunds
                SET status = 'failed', failure_reason = ?
                WHERE id = ?
                """,
                (failure_reason, refund_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status = 'review_required', updated_at = ? WHERE id = ?",
                (failed_at, order_id),
            )
            _append_admin_refund_event(
                conn,
                order_id=order_id,
                payment_id=payment_id,
                event_type="refund_create_failed",
                provider_status="failed",
                details={"failure_reason": failure_reason, "idempotency_key": clean_key},
                admin_id=admin_id,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        raise StripeRefundActionError(
            "STRIPE_REFUND_FAILED",
            f"Failed to create Stripe refund: {failure_reason}",
            502,
        ) from exc

    provider_refund_id = _stripe_object_value(stripe_refund, "id")
    provider_status = _stripe_object_value(stripe_refund, "status")
    conn.execute(
        """
        UPDATE payment_refunds
        SET provider_refund_id = ?
        WHERE id = ?
        """,
        (str(provider_refund_id) if provider_refund_id else None, refund_id),
    )
    _append_admin_refund_event(
        conn,
        order_id=order_id,
        payment_id=payment_id,
        event_type="stripe_refund_created",
        provider_status="refund_pending",
        details={
            "provider_refund_id": provider_refund_id,
            "provider_status": provider_status,
            "idempotency_key": clean_key,
        },
        admin_id=admin_id,
    )
    conn.commit()
    return _refund_row(conn, refund_id)


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
    order, existing_url = prepare_retry_session(conn, order_id, payment_return_token)
    if existing_url:
        return existing_url

    return create_retry_checkout_session(conn, order, success_url, cancel_url, stripe_secret_key)


def prepare_retry_session(
    conn: sqlite3.Connection,
    order_id: str,
    payment_return_token: str,
) -> tuple[OrderData, str | None]:
    """Validate a card retry request and return any reusable Checkout URL.

    This performs only local checks. Routes can call it before consuming the
    Stripe-session creation rate limit, so bad tokens and existing reusable URLs
    do not burn the customer's fresh-session budget.
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
            return order, existing_url

    return order, None


def construct_stripe_webhook_event(
    raw_body: bytes,
    sig_header: str,
    webhook_secret: str,
    stripe_secret_key: str,
) -> Any:
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
        details: dict[str, object] = {
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
                    "UPDATE orders SET payment_status = 'review_required' "
                    "WHERE id = ? AND payment_status IN "
                    "('pending', 'failed', 'review_required')",
                    (order_id,),
                )
                if payment_id:
                    conn.execute(
                        """
                        UPDATE payments
                        SET stripe_payment_intent_id = COALESCE(?, stripe_payment_intent_id),
                            provider_status = 'review_required',
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (payment_intent_id, now, payment_id),
                    )
                processing_status = "requires_review"
                provider_status = "review_required"
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
    """Handle checkout.session.expired: set payment_status='review_required'.

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
            "UPDATE orders SET payment_status = 'review_required'"
            " WHERE id = ? AND payment_status = 'pending'"
            " AND stripe_checkout_session_id = ?",
            (order_id, stripe_session_id),
        )
        if cur.rowcount and payment_id:
            conn.execute(
                """
                UPDATE payments
                SET provider_status = 'review_required', updated_at = ?
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
            provider_status="review_required" if cur.rowcount else "ignored",
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


def handle_refund_updated(
    conn: sqlite3.Connection,
    event_id: str,
    event_type: str,
    provider_refund_id: str | None,
    payment_intent_id: str | None,
    now: str,
    *,
    amount_cents: int | None = None,
    status: str | None = None,
    failure_reason: str | None = None,
    event_created: int | None = None,
    livemode: bool | None = None,
) -> bool:
    """Handle Stripe refund status updates and finalize local refund records."""
    resolved_order_id: str | None = None
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, order_id, event_type, received_at)"
            " VALUES (?, NULL, ?, ?)",
            (event_id, event_type, now),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            return False

        refund = None
        if provider_refund_id:
            refund = conn.execute(
                """
                SELECT * FROM payment_refunds
                WHERE provider = 'stripe' AND provider_refund_id = ?
                LIMIT 1
                """,
                (provider_refund_id,),
            ).fetchone()

        if refund is not None:
            resolved_order_id = refund["order_id"]
            payment_id = refund["payment_id"]
            refund_amount = int(refund["amount_cents"])
        else:
            resolved_order_id = _order_id_for_payment_intent(conn, payment_intent_id)
            payment_id = (
                _payment_id_for_order(conn, resolved_order_id) if resolved_order_id else None
            )
            refund_amount = amount_cents or 0

        provider_status = status or "unknown"
        processing_status = "unmatched"
        if refund is not None and provider_status == "succeeded":
            conn.execute(
                """
                UPDATE payment_refunds
                SET status = 'succeeded', confirmed_at = COALESCE(confirmed_at, ?),
                    failure_reason = NULL
                WHERE id = ?
                """,
                (now, refund["id"]),
            )
            total_refunded = conn.execute(
                """
                SELECT COALESCE(SUM(amount_cents), 0) AS total
                FROM payment_refunds
                WHERE order_id = ? AND provider = 'stripe' AND status = 'succeeded'
                """,
                (resolved_order_id,),
            ).fetchone()["total"]
            order_total = conn.execute(
                "SELECT total_cents FROM orders WHERE id = ?",
                (resolved_order_id,),
            ).fetchone()["total_cents"]
            new_payment_status = (
                "refunded" if int(total_refunded) >= int(order_total) else "partially_refunded"
            )
            conn.execute(
                "UPDATE orders SET payment_status = ?, updated_at = ? WHERE id = ?",
                (new_payment_status, now, resolved_order_id),
            )
            if payment_id:
                conn.execute(
                    "UPDATE payments SET provider_status = ?, updated_at = ? WHERE id = ?",
                    (new_payment_status, now, payment_id),
                )
            provider_status = new_payment_status
            processing_status = "processed"
        elif refund is not None and provider_status == "failed":
            conn.execute(
                """
                UPDATE payment_refunds
                SET status = 'failed', failure_reason = ?
                WHERE id = ?
                """,
                (failure_reason, refund["id"]),
            )
            conn.execute(
                "UPDATE orders SET payment_status = 'review_required', updated_at = ? WHERE id = ?",
                (now, resolved_order_id),
            )
            if payment_id:
                conn.execute(
                    "UPDATE payments SET provider_status = 'review_required', updated_at = ? WHERE id = ?",
                    (now, payment_id),
                )
            provider_status = "failed"
            processing_status = "processed"
        elif refund is not None:
            processing_status = "processed"

        if resolved_order_id:
            conn.execute(
                "UPDATE stripe_events SET order_id = ? WHERE event_id = ?",
                (resolved_order_id, event_id),
            )

        _append_stripe_payment_event(
            conn,
            event_id=event_id,
            event_type=event_type,
            order_id=resolved_order_id,
            payment_id=payment_id,
            provider_status=provider_status,
            processing_status=processing_status,
            details={
                "provider_refund_id": provider_refund_id,
                "payment_intent_id": payment_intent_id,
                "amount_cents": refund_amount or amount_cents,
                "stripe_refund_status": status,
                "failure_reason": failure_reason,
                "event_created": event_created,
                "livemode": livemode,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info("stripe_refund_updated", order_id=resolved_order_id, event_id=event_id)
    return True


def _payment_status_for_dispute(event_type: str, dispute_status: str | None) -> str:
    normalized = (dispute_status or "").lower()
    if normalized == "won":
        return "dispute_won"
    if normalized == "lost":
        return "dispute_lost"
    if event_type.endswith(".closed") and normalized in {"warning_closed", "closed"}:
        return "dispute_won"
    return "dispute_open"


def handle_dispute_event(
    conn: sqlite3.Connection,
    event_id: str,
    event_type: str,
    order_id: str | None,
    payment_intent_id: str | None,
    dispute_id: str | None,
    dispute_status: str | None,
    now: str,
    *,
    amount_cents: int | None = None,
    evidence_due_by: int | None = None,
    event_created: int | None = None,
    livemode: bool | None = None,
) -> bool:
    """Record Stripe dispute evidence and update the payment review status."""
    resolved_order_id = order_id or _order_id_for_payment_intent(conn, payment_intent_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, order_id, event_type, received_at)"
            " VALUES (?, ?, ?, ?)",
            (event_id, resolved_order_id, event_type, now),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            return False

        payment_id = _payment_id_for_order(conn, resolved_order_id) if resolved_order_id else None
        provider_status = _payment_status_for_dispute(event_type, dispute_status)
        if resolved_order_id:
            conn.execute(
                "UPDATE orders SET payment_status = ?, updated_at = ? WHERE id = ?",
                (provider_status, now, resolved_order_id),
            )
            if payment_id:
                conn.execute(
                    "UPDATE payments SET provider_status = ?, updated_at = ? WHERE id = ?",
                    (provider_status, now, payment_id),
                )

        _append_stripe_payment_event(
            conn,
            event_id=event_id,
            event_type=event_type,
            order_id=resolved_order_id,
            payment_id=payment_id,
            provider_status=provider_status,
            processing_status="processed" if resolved_order_id else "unmatched",
            details={
                "dispute_id": dispute_id,
                "dispute_status": dispute_status,
                "payment_intent_id": payment_intent_id,
                "amount_cents": amount_cents,
                "evidence_due_by": evidence_due_by,
                "event_created": event_created,
                "livemode": livemode,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    logger.info("stripe_dispute_event", order_id=resolved_order_id, event_id=event_id)
    return True


def _now_str() -> str:
    return datetime.now(UTC).strftime(_DT_FMT)
