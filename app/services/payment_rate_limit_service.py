"""SQLite-backed rate limits for payment and checkout surfaces."""

import sqlite3
from dataclasses import dataclass

CHECKOUT_SESSION_LIMIT = 5
CHECKOUT_SESSION_WINDOW_SECONDS = 15 * 60
CHECKOUT_IP_LIMIT = 20
CHECKOUT_IP_WINDOW_SECONDS = 60 * 60
STRIPE_SESSION_ORDER_LIMIT = 3
STRIPE_SESSION_SESSION_LIMIT = 10
STRIPE_SESSION_SESSION_WINDOW_SECONDS = 60 * 60
PAY_ON_DELIVERY_SESSION_LIMIT = 2
PAY_ON_DELIVERY_SESSION_WINDOW_SECONDS = 60 * 60
PAY_ON_DELIVERY_IP_LIMIT = 5
PAY_ON_DELIVERY_IP_WINDOW_SECONDS = 24 * 60 * 60
PAYMENT_STATUS_POLL_LIMIT = 60
PAYMENT_STATUS_POLL_WINDOW_SECONDS = 5 * 60

_CHECKOUT_ACTION = "checkout_order_create"
_STRIPE_SESSION_ACTION = "stripe_session_create"
_PAY_ON_DELIVERY_ACTION = "pay_on_delivery_order_create"
_PAYMENT_STATUS_POLL_ACTION = "payment_status_poll"
_UNKNOWN_KEY = "unknown"


@dataclass(frozen=True)
class _RateLimitBucket:
    scope: str
    key: str
    limit: int
    window_modifier: str | None
    window_seconds: int
    message: str


class PaymentRateLimitExceededError(Exception):
    """Raised when a payment surface rate limit is exceeded."""

    def __init__(self, message: str, *, scope: str, limit: int, window_seconds: int) -> None:
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(message)


def _key(value: str | None) -> str:
    return value or _UNKNOWN_KEY


def _count_bucket(
    conn: sqlite3.Connection,
    *,
    action: str,
    bucket: _RateLimitBucket,
) -> int:
    if bucket.window_modifier is None:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM payment_rate_limit_events
            WHERE action = %s AND scope = %s AND key = %s
            """,
            (action, bucket.scope, bucket.key),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM payment_rate_limit_events
            WHERE action = %s
              AND scope = %s
              AND key = %s
              AND created_at >= datetime('now', %s)
            """,
            (action, bucket.scope, bucket.key, bucket.window_modifier),
        ).fetchone()
    return int(row["count"] if row else 0)


def _check_buckets(
    conn: sqlite3.Connection,
    *,
    action: str,
    buckets: list[_RateLimitBucket],
) -> None:
    for bucket in buckets:
        if _count_bucket(conn, action=action, bucket=bucket) >= bucket.limit:
            raise PaymentRateLimitExceededError(
                bucket.message,
                scope=bucket.scope,
                limit=bucket.limit,
                window_seconds=bucket.window_seconds,
            )


def _consume_rate_limit(
    conn: sqlite3.Connection,
    *,
    action: str,
    buckets: list[_RateLimitBucket],
) -> None:
    """Check all buckets, then record the accepted attempt atomically."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "DELETE FROM payment_rate_limit_events WHERE created_at < datetime('now', '-2 days')"
        )
        _check_buckets(conn, action=action, buckets=buckets)

        conn.executemany(
            """
            INSERT INTO payment_rate_limit_events (action, scope, key)
            VALUES (%s, %s, %s)
            """,
            [(action, bucket.scope, bucket.key) for bucket in buckets],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def consume_checkout_order_rate_limit(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    ip_address: str | None,
) -> None:
    """Limit checkout/order creation attempts per session and per IP."""
    _consume_rate_limit(
        conn,
        action=_CHECKOUT_ACTION,
        buckets=[
            _RateLimitBucket(
                scope="session",
                key=_key(session_id),
                limit=CHECKOUT_SESSION_LIMIT,
                window_modifier="-15 minutes",
                window_seconds=CHECKOUT_SESSION_WINDOW_SECONDS,
                message="Too many checkout attempts. Please try again later.",
            ),
            _RateLimitBucket(
                scope="ip",
                key=_key(ip_address),
                limit=CHECKOUT_IP_LIMIT,
                window_modifier="-1 hour",
                window_seconds=CHECKOUT_IP_WINDOW_SECONDS,
                message="Too many checkout attempts from this network. Please try again later.",
            ),
        ],
    )


def _stripe_session_bucket(session_id: str) -> _RateLimitBucket:
    return _RateLimitBucket(
        scope="session",
        key=_key(session_id),
        limit=STRIPE_SESSION_SESSION_LIMIT,
        window_modifier="-1 hour",
        window_seconds=STRIPE_SESSION_SESSION_WINDOW_SECONDS,
        message="Too many Stripe Checkout attempts. Please try again later.",
    )


def assert_stripe_session_rate_limit_available(
    conn: sqlite3.Connection,
    *,
    session_id: str,
) -> None:
    """Check the per-session Stripe session bucket without recording an attempt."""
    _check_buckets(
        conn,
        action=_STRIPE_SESSION_ACTION,
        buckets=[_stripe_session_bucket(session_id)],
    )


def consume_stripe_session_rate_limit(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    session_id: str,
) -> None:
    """Limit Stripe Checkout Session creation per order and per session."""
    _consume_rate_limit(
        conn,
        action=_STRIPE_SESSION_ACTION,
        buckets=[
            _RateLimitBucket(
                scope="order",
                key=_key(order_id),
                limit=STRIPE_SESSION_ORDER_LIMIT,
                window_modifier=None,
                window_seconds=0,
                message="Too many Stripe Checkout sessions for this order.",
            ),
            _stripe_session_bucket(session_id),
        ],
    )


def consume_pay_on_delivery_rate_limit(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    ip_address: str | None,
) -> None:
    """Limit pay-on-delivery order attempts more strictly than generic checkout."""
    _consume_rate_limit(
        conn,
        action=_PAY_ON_DELIVERY_ACTION,
        buckets=[
            _RateLimitBucket(
                scope="session",
                key=_key(session_id),
                limit=PAY_ON_DELIVERY_SESSION_LIMIT,
                window_modifier="-1 hour",
                window_seconds=PAY_ON_DELIVERY_SESSION_WINDOW_SECONDS,
                message="Too many pay-on-delivery attempts. Please try again later.",
            ),
            _RateLimitBucket(
                scope="ip",
                key=_key(ip_address),
                limit=PAY_ON_DELIVERY_IP_LIMIT,
                window_modifier="-1 day",
                window_seconds=PAY_ON_DELIVERY_IP_WINDOW_SECONDS,
                message=(
                    "Too many pay-on-delivery attempts from this network. Please try again later."
                ),
            ),
        ],
    )


def consume_payment_status_poll_rate_limit(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    ip_address: str | None,
) -> None:
    """Limit payment-status polling after Stripe return."""
    _consume_rate_limit(
        conn,
        action=_PAYMENT_STATUS_POLL_ACTION,
        buckets=[
            _RateLimitBucket(
                scope="session",
                key=_key(session_id),
                limit=PAYMENT_STATUS_POLL_LIMIT,
                window_modifier="-5 minutes",
                window_seconds=PAYMENT_STATUS_POLL_WINDOW_SECONDS,
                message="Too many payment status checks. Please try again later.",
            ),
            _RateLimitBucket(
                scope="ip",
                key=_key(ip_address),
                limit=PAYMENT_STATUS_POLL_LIMIT,
                window_modifier="-5 minutes",
                window_seconds=PAYMENT_STATUS_POLL_WINDOW_SECONDS,
                message="Too many payment status checks. Please try again later.",
            ),
        ],
    )
