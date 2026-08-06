"""Email service — orchestrates the durable-outbox send path.

The sweeper (`app/main.py`) calls `drain_email_outbox()` on a ~15s tick. For
each eligible `order_emails` row it runs the send path here:

    fresh DB read (locale from orders.locale) → suppression check → acquire
    DB claim → render → provider.send → record terminal/attempt state.

Everything is caught: an email failure NEVER propagates to Layer 1. Idempotency
is entirely DB-driven (claim table + partial UNIQUE index) because ZeptoMail has
no send-level idempotency key (design Decisions 11, 14, 25). Logs bind
`order_id` + `email_event` since `request_id` is unavailable off-request
(Decision 22).
"""

import json
from datetime import UTC, datetime, timedelta

import structlog

from app.config import Settings, get_settings
from app.constants import STATUS_TO_EMAIL_EVENT
from app.database import DbConnection, IntegrityError, get_db
from app.email.providers import (
    EmailProvider,
    PermanentEmailError,
    TransientEmailError,
    get_email_provider,
)
from app.email.redaction import redact_recipient
from app.email.renderer import TemplateMissingError, render_template
from app.legal import get_public_legal_identity, localized_policy_url
from app.services.order_service import OrderData, _fetch_order_with_items

logger = structlog.get_logger(__name__)

_DT_FMT = "%Y-%m-%d %H:%M:%S"

# Retry policy (design Decision 25).
MAX_ATTEMPTS = 5
CLAIM_LEASE_SECONDS = 300  # a crashed worker's claim expires after 5 min
_BACKOFF_BASE_SECONDS = 30  # 30s, 60s, 120s, ...
_SWEEP_BATCH_LIMIT = 50

__all__ = [
    "MAX_ATTEMPTS",
    "drain_email_outbox",
    "event_for_status",
    "format_price",
    "queue_order_email",
    "recipient_for",
    "send_admin_alert",
    "send_order_email",
]


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


def format_price(cents: int, locale: str) -> str:
    """Format an integer cent amount as a locale display string.

    EN → "€45.00"; BG → "45.00 лв" (email-templates spec).
    """
    amount = f"{cents / 100:.2f}"
    if locale == "bg":
        return f"{amount} лв"
    return f"€{amount}"


def _delivery_method_label(method: str | None, locale: str) -> str | None:
    if method == "office":
        return "До офис/автомат" if locale == "bg" else "Office or locker pickup"
    if method == "door":
        return "До адрес" if locale == "bg" else "Door delivery"
    if method == "internal":
        return "Доставка от Atelier Marie" if locale == "bg" else "Atelier Marie delivery"
    return None


def _office_type_label(office_type: str | None, locale: str) -> str | None:
    if office_type == "apt":
        return "Автомат" if locale == "bg" else "Locker"
    if office_type == "office":
        return "Офис" if locale == "bg" else "Office"
    return None


def _courier_label(courier: str | None) -> str | None:
    if courier == "speedy":
        return "Speedy"
    if courier == "econt":
        return "Econt"
    return courier


def _address_line(details: dict, locale: str) -> str | None:
    street = details.get("street")
    if not street:
        return None
    parts = [street]
    building = details.get("building")
    apartment = details.get("apartment")
    if building:
        label = "вх./сгр." if locale == "bg" else "building"
        parts.append(f"{label} {building}")
    if apartment:
        label = "ап." if locale == "bg" else "apt."
        parts.append(f"{label} {apartment}")
    return ", ".join(parts)


def _build_delivery_email_context(order_data: OrderData, locale: str) -> dict:
    """Return localized delivery fields shared by customer/admin emails."""
    method = order_data.get("delivery_method")
    courier = order_data.get("delivery_courier")
    details = order_data.get("delivery_details") or {}

    labels = {
        "office": "Офис" if locale == "bg" else "Office",
        "type": "Тип" if locale == "bg" else "Type",
        "city": "Град/населено място" if locale == "bg" else "City/place",
        "address": "Адрес" if locale == "bg" else "Address",
        "phone": "Телефон" if locale == "bg" else "Phone",
    }

    delivery_lines: list[str] = []
    if method == "office":
        office_name = details.get("office_name")
        office_type = _office_type_label(details.get("office_type"), locale)
        city = details.get("city")
        if office_name:
            delivery_lines.append(f"{labels['office']}: {office_name}")
        if office_type:
            delivery_lines.append(f"{labels['type']}: {office_type}")
        if city:
            delivery_lines.append(f"{labels['city']}: {city}")
    elif method in {"door", "internal"}:
        address = _address_line(details, locale)
        city_parts = [part for part in (details.get("postal_code"), details.get("city")) if part]
        if address:
            delivery_lines.append(f"{labels['address']}: {address}")
        if city_parts:
            delivery_lines.append(f"{labels['city']}: {' '.join(city_parts)}")

    phone = details.get("phone")
    if phone:
        delivery_lines.append(f"{labels['phone']}: {phone}")

    return {
        "delivery_method_display": _delivery_method_label(method, locale),
        "delivery_courier_display": _courier_label(courier),
        "delivery_lines": delivery_lines,
        "shipping_is_fallback": order_data.get("shipping_is_fallback", False),
    }


def _latest_payment_review_context(conn: DbConnection, order_id: str) -> dict:
    """Return safe metadata for the latest payment review event."""
    row = conn.execute(
        """
        SELECT stripe_event_id, details
        FROM payment_events
        WHERE order_id = %s AND processing_status = 'requires_review'
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (order_id,),
    ).fetchone()
    if row is None:
        return {}
    try:
        details = json.loads(row["details"] or "{}")
    except json.JSONDecodeError:
        details = {}
    return {
        "reason": details.get("ignored_reason") or details.get("reason") or "requires_review",
        "checkout_session_id": details.get("checkout_session_id"),
        "payment_intent_id": details.get("payment_intent_id"),
        "stripe_event_id": row["stripe_event_id"],
    }


def _build_email_context(
    order_data: OrderData,
    locale: str,
    settings: Settings,
    *,
    payment_review: dict | None = None,
) -> dict:
    """Build the Jinja2 context for an order email.

    Prices are converted to display strings here — templates never do
    arithmetic (email-templates spec).
    """
    items = [
        {
            "product_name": item["product_name"],
            "quantity": item["quantity"],
            "price_display": format_price(item["price_cents"], locale),
            "line_total_display": format_price(item["price_cents"] * item["quantity"], locale),
        }
        for item in order_data["items"]
    ]
    order_id = order_data["id"]
    display_order_number = order_data.get("order_number") or order_id[:8]
    payment_review = payment_review or {}
    legal_identity = get_public_legal_identity()
    context = {
        "order_id_short": order_id[:8],
        "order_number": display_order_number,
        "customer_name": order_data["customer_name"],
        "customer_email": order_data["customer_email"],
        "items": items,
        "items_total_display": format_price(order_data["items_total_cents"], locale),
        "shipping_display": format_price(order_data["shipping_cents"], locale),
        "total_display": format_price(order_data["total_cents"], locale),
        "tracking_carrier": order_data["tracking_carrier"],
        "tracking_number": order_data["tracking_number"],
        "tracking_url": order_data["tracking_url"],
        "admin_order_url": f"{settings.frontend_url.rstrip('/')}/admin/orders/{order_id}",
        "terms_url": localized_policy_url(settings.frontend_url, locale, "terms"),
        "privacy_url": localized_policy_url(settings.frontend_url, locale, "privacy"),
        "cookies_url": localized_policy_url(settings.frontend_url, locale, "cookies"),
        "contact_url": localized_policy_url(settings.frontend_url, locale, "contact"),
        "trader_name": legal_identity["trading_name"],
        "trader_legal_name": legal_identity["legal_name"],
        "trader_contact_email": legal_identity["contact_email"],
        "trader_address": legal_identity["geographic_address"],
        "trader_registration_number": legal_identity["registration_number"],
        "trader_vat_number": legal_identity["vat_number"],
        # Payment fields (payment-integration) — safe defaults for legacy rows.
        "payment_method": order_data.get("payment_method", "cod"),
        "payment_status": order_data.get("payment_status", "cod_pending"),
        "stripe_checkout_session_id": order_data.get("stripe_checkout_session_id"),
        "stripe_payment_intent_id": order_data.get("stripe_payment_intent_id"),
        "payment_review_reason": payment_review.get("reason") or "requires_review",
        "payment_review_checkout_session_id": payment_review.get("checkout_session_id")
        or order_data.get("stripe_checkout_session_id"),
        "payment_review_payment_intent_id": payment_review.get("payment_intent_id")
        or order_data.get("stripe_payment_intent_id"),
        "payment_review_stripe_event_id": payment_review.get("stripe_event_id"),
        # Bank transfer details from config — only populated when method is bank_transfer.
        "bank_iban": settings.bank_iban,
        "bank_bic": settings.bank_bic,
        "bank_name": settings.bank_name,
    }
    context.update(_build_delivery_email_context(order_data, locale))
    return context


def _recipient_for(order_data: OrderData, event: str, settings: Settings) -> str | None:
    """Resolve the recipient address for an event, or None if not sendable.

    Kept for reference/tests; the live send path reads the recipient recorded on
    the queued row, and routes use `recipient_for` at queue time.
    """
    if event == "admin_new_order":
        return settings.admin_notification_email or None
    return order_data["customer_email"]


def recipient_for(customer_email: str, event: str, settings: Settings) -> str:
    """Resolve the recipient to record on a queued row (routes use this).

    Returns an empty string for admin_new_order when no admin address is
    configured — the send path then records `skipped_suppressed` (no recipient),
    satisfying the "no admin email configured → no send, no error" scenario.
    """
    if event == "admin_new_order":
        return settings.admin_notification_email or ""
    return customer_email


def queue_order_email(
    conn: DbConnection,
    order_id: str,
    event: str,
    recipient: str,
) -> None:
    """Insert a durable `queued` outbox row (design Decision 25).

    Called inside the caller's transaction (the checkout BEGIN/COMMIT or the
    admin status-update connection) so the intent commits atomically with the
    order state change and survives any crash. The sweeper delivers it later.
    """
    conn.execute(
        "INSERT INTO order_emails (order_id, event, recipient, status) "
        "VALUES (%s, %s, %s, 'queued')",
        (order_id, event, recipient or ""),
    )


# ---------------------------------------------------------------------------
# DB helpers (idempotency: claim table + partial UNIQUE index)
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _is_suppressed(conn: DbConnection, email: str) -> bool:
    row = conn.execute("SELECT 1 FROM suppressed_emails WHERE email = %s", (email,)).fetchone()
    return row is not None


def _already_sent(conn: DbConnection, order_id: str, event: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM order_emails WHERE order_id = %s AND event = %s AND status = 'sent'",
        (order_id, event),
    ).fetchone()
    return row is not None


def _try_acquire_claim(conn: DbConnection, order_id: str, event: str) -> bool:
    """Atomically claim (order_id, event) for this sweeper.

    Returns True if the claim was acquired (fresh, or taken over from an expired
    in_flight / failed claim), False if another live sender holds it or a send
    already succeeded. The unique key plus transaction keep the claim atomic.
    """
    now = _now()
    now_s = now.strftime(_DT_FMT)
    lease_s = (now + timedelta(seconds=CLAIM_LEASE_SECONDS)).strftime(_DT_FMT)

    with conn.transaction():
        cursor = conn.execute(
            """
            INSERT INTO order_email_send_claims
                (order_id, event, status, lease_expires_at, updated_at)
            VALUES (%s, %s, 'in_flight', %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (order_id, event, lease_s, now_s),
        )
        if cursor.rowcount == 1:
            return True

        # Row exists — take it over only if failed or the lease has expired.
        cursor = conn.execute(
            """
            UPDATE order_email_send_claims
            SET status = 'in_flight', lease_expires_at = %s, updated_at = %s
            WHERE order_id = %s AND event = %s
              AND status != 'sent'
              AND (status = 'failed' OR lease_expires_at IS NULL OR lease_expires_at < %s)
            """,
            (lease_s, now_s, order_id, event, now_s),
        )
        return cursor.rowcount == 1


def _claim_status(conn: DbConnection, order_id: str, event: str) -> str | None:
    row = conn.execute(
        "SELECT status FROM order_email_send_claims WHERE order_id = %s AND event = %s",
        (order_id, event),
    ).fetchone()
    return row["status"] if row else None


def _release_claim(conn: DbConnection, order_id: str, event: str, status: str) -> None:
    conn.execute(
        "UPDATE order_email_send_claims SET status = %s, updated_at = %s "
        "WHERE order_id = %s AND event = %s",
        (status, _now().strftime(_DT_FMT), order_id, event),
    )


def _update_row(
    conn: DbConnection,
    row_id: int,
    status: str,
    *,
    reason: str | None = None,
    attempts: int | None = None,
    next_attempt_at: str | None = None,
) -> None:
    """Update an order_emails row's terminal/attempt state.

    Never raises to the caller: a logging/audit failure must not propagate
    (email-service spec). IntegrityError on the partial UNIQUE index (another
    'sent' row already exists) is folded into a duplicate skip.
    """
    fields = ["status = %s", "reason = %s", "sent_at = %s"]
    params: list = [status, reason, _now().strftime(_DT_FMT)]
    if attempts is not None:
        fields.append("attempts = %s")
        params.append(attempts)
    if next_attempt_at is not None or status != "failed":
        fields.append("next_attempt_at = %s")
        params.append(next_attempt_at)
    params.append(row_id)
    try:
        with conn.transaction():
            conn.execute(f"UPDATE order_emails SET {', '.join(fields)} WHERE id = %s", params)
    except IntegrityError:
        # A concurrent worker already recorded 'sent' for this (order_id, event).
        # The failed UPDATE is contained by the savepoint above, so the connection
        # is not left in a poisoned (InFailedSqlTransaction) state and this
        # recovery UPDATE can run on the same connection.
        conn.execute(
            "UPDATE order_emails SET status = 'skipped_duplicate', reason = %s, sent_at = %s "
            "WHERE id = %s",
            ("duplicate sent row", _now().strftime(_DT_FMT), row_id),
        )
    except Exception:
        logger.exception("email_row_update_failed", row_id=row_id)


def _backoff_next_attempt(attempts: int) -> str:
    """Exponential backoff timestamp: base * 2^(attempts-1)."""
    delay = _BACKOFF_BASE_SECONDS * (2 ** max(0, attempts - 1))
    return (_now() + timedelta(seconds=delay)).strftime(_DT_FMT)


def _emit_admin_failure_alert(order_id: str, event: str, reason: str) -> None:
    """Structured error log flagging a poison message for a human (Decision 25).

    A truly provider-independent push (SMS/Telegram) is out of scope; the order
    itself is already a durable admin-dashboard row, so this is the alert.
    """
    logger.error(
        "email_failed_permanent_admin_alert",
        order_id=order_id,
        email_event=event,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Send path (used by the sweeper)
# ---------------------------------------------------------------------------


def _process_outbox_row(
    row_id: int,
    *,
    provider: EmailProvider,
    settings: Settings,
) -> None:
    """Drive one order_emails row to a terminal/attempt state.

    Opens its own DB connection(s) (task 7.9 — runs in the sweeper, not a
    request). The network send happens with no DB connection held.
    """
    # Phase 1: fresh read, suppression check, claim acquisition.
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, order_id, event, recipient, status, attempts "
            "FROM order_emails WHERE id = %s",
            (row_id,),
        ).fetchone()
        if row is None or row["status"] not in ("queued", "failed"):
            return

        order_id = row["order_id"]
        event = row["event"]
        recipient = row["recipient"]
        attempts = row["attempts"]
        log = logger.bind(order_id=order_id, email_event=event)

        if _already_sent(conn, order_id, event):
            _update_row(conn, row_id, "skipped_duplicate", reason="already sent")
            log.info("email_skipped_duplicate")
            return

        if recipient and _is_suppressed(conn, recipient):
            _update_row(conn, row_id, "skipped_suppressed", reason="recipient suppressed")
            log.info("email_skipped_suppressed", recipient=redact_recipient(recipient))
            return

        order = _fetch_order_with_items(conn, order_id)
        if order is None:
            _update_row(conn, row_id, "failed_permanent", reason="order not found")
            log.error("email_order_missing")
            return

        if not recipient:
            # e.g. admin_new_order queued but ADMIN_NOTIFICATION_EMAIL is empty.
            _update_row(conn, row_id, "skipped_suppressed", reason="no recipient configured")
            log.info("email_skipped_no_recipient")
            return

        if not _try_acquire_claim(conn, order_id, event):
            claim = _claim_status(conn, order_id, event)
            if claim == "sent":
                _update_row(conn, row_id, "skipped_duplicate", reason="already sent")
                log.info("email_skipped_duplicate")
            else:
                log.info("email_claim_in_flight", claim_status=claim)
            return

        locale = order["locale"]
        payment_review = (
            _latest_payment_review_context(conn, order_id)
            if event == "admin_payment_review_required"
            else None
        )
        context = _build_email_context(
            order,
            locale,
            settings,
            payment_review=payment_review,
        )

    # Phase 2: render + network (no DB connection held).
    try:
        subject, body = render_template(event, locale, context)
    except TemplateMissingError as exc:
        with get_db() as conn:
            _update_row(conn, row_id, "failed_permanent", reason=str(exc))
            _release_claim(conn, order_id, event, "failed")
        _emit_admin_failure_alert(order_id, event, f"template missing: {exc}")
        return

    try:
        message_id = provider.send(
            to=recipient,
            subject=subject,
            body=body,
            reply_to=settings.email_reply_to,
            tags=[event],
        )
    except TransientEmailError as exc:
        attempts += 1
        with get_db() as conn:
            if attempts >= MAX_ATTEMPTS:
                _update_row(conn, row_id, "failed_permanent", reason=str(exc), attempts=attempts)
                _release_claim(conn, order_id, event, "failed")
                _emit_admin_failure_alert(order_id, event, f"max attempts: {exc}")
            else:
                _update_row(
                    conn,
                    row_id,
                    "failed",
                    reason=str(exc),
                    attempts=attempts,
                    next_attempt_at=_backoff_next_attempt(attempts),
                )
                _release_claim(conn, order_id, event, "failed")
        log.warning("email_send_transient_failure", attempts=attempts, error=str(exc))
        return
    except PermanentEmailError as exc:
        attempts += 1
        with get_db() as conn:
            _update_row(conn, row_id, "failed_permanent", reason=str(exc), attempts=attempts)
            _release_claim(conn, order_id, event, "failed")
        _emit_admin_failure_alert(order_id, event, f"permanent: {exc}")
        log.error("email_send_permanent_failure", error=str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - never let an email crash the sweeper
        attempts += 1
        with get_db() as conn:
            if attempts >= MAX_ATTEMPTS:
                _update_row(conn, row_id, "failed_permanent", reason=str(exc), attempts=attempts)
                _release_claim(conn, order_id, event, "failed")
                _emit_admin_failure_alert(order_id, event, f"unexpected: {exc}")
            else:
                _update_row(
                    conn,
                    row_id,
                    "failed",
                    reason=str(exc),
                    attempts=attempts,
                    next_attempt_at=_backoff_next_attempt(attempts),
                )
                _release_claim(conn, order_id, event, "failed")
        log.warning("email_send_unexpected_error", attempts=attempts, error=str(exc))
        return

    # Phase 3: success.
    with get_db() as conn:
        _update_row(conn, row_id, "sent", reason=message_id, attempts=attempts + 1)
        _release_claim(conn, order_id, event, "sent")
    log.info("email_sent", recipient=redact_recipient(recipient), message_id=message_id)


def drain_email_outbox(
    *,
    provider: EmailProvider | None = None,
    settings: Settings | None = None,
) -> int:
    """Process all currently-eligible outbox rows. Returns the count processed.

    Selects rows in one connection, then processes each in its own connection
    (task 8b.3 / 7.9). Callable directly in tests — no running loop required.
    """
    settings = settings or get_settings()
    provider = provider or get_email_provider(settings)

    with get_db() as conn:
        now_s = _now().strftime(_DT_FMT)
        rows = conn.execute(
            """
            SELECT id FROM order_emails
            WHERE status IN ('queued', 'failed')
              AND (next_attempt_at IS NULL OR next_attempt_at <= %s)
              AND attempts < %s
            ORDER BY id
            LIMIT %s
            """,
            (now_s, MAX_ATTEMPTS, _SWEEP_BATCH_LIMIT),
        ).fetchall()
        row_ids = [r["id"] for r in rows]

    for row_id in row_ids:
        try:
            _process_outbox_row(row_id, provider=provider, settings=settings)
        except Exception:
            # A single poison row must never stop the drain.
            logger.exception("email_outbox_row_crashed", row_id=row_id)

    return len(row_ids)


# ---------------------------------------------------------------------------
# Convenience entry points
# ---------------------------------------------------------------------------


def send_order_email(order_id: str, event: str) -> None:
    """Attempt to send the queued email for (order_id, event) immediately.

    Thin wrapper over the sweeper's per-row path — mostly for tests and any
    future admin "re-send" action. The normal delivery path is the outbox
    sweeper. Locale is read from `orders.locale` inside the send path, never
    from a session (task 7.6).
    """
    settings = get_settings()
    provider = get_email_provider(settings)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM order_emails WHERE order_id = %s AND event = %s "
            "AND status IN ('queued', 'failed') ORDER BY id LIMIT 1",
            (order_id, event),
        ).fetchone()
        row_id = row["id"] if row else None
    if row_id is not None:
        _process_outbox_row(row_id, provider=provider, settings=settings)


def send_admin_alert(order_id: str) -> None:
    """Send the admin new-order alert for an order (event=admin_new_order).

    The alert normally rides the outbox like any other event; this is a direct
    convenience used in tests. No-op if ADMIN_NOTIFICATION_EMAIL is unset.
    """
    send_order_email(order_id, "admin_new_order")


def event_for_status(status: str) -> str | None:
    """OrderStatus → EmailEvent (None = no customer email). Re-exported for routes."""
    return STATUS_TO_EMAIL_EVENT.get(status)
