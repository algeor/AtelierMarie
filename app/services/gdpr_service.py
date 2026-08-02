"""GDPR helpers for email PII stores (email-notifications Decision 23).

There is no consolidated erasure job in the codebase yet; these functions give
a future job (or an admin action) the two operations Decision 23 requires:
scrub `order_emails.recipient` for an erased order, and age out
`suppressed_emails`. Anonymous checkouts have no `user_id`, so PII here is keyed
by `order_id` (join to the erased order), not by user.
"""

import sqlite3

import structlog

from app.database import get_db
from app.services import analytics_service

logger = structlog.get_logger(__name__)

# Placeholder written over an erased recipient (keeps the row for audit shape).
_ERASED_PLACEHOLDER = "[erased]"


def anonymize_order_emails(order_id: str, conn: sqlite3.Connection | None = None) -> int:
    """Scrub recipient addresses on all order_emails rows for an order.

    Returns the number of rows updated. Preserves row/audit structure (status,
    event, timestamps) — only the PII (recipient) is removed.
    """

    def _run(c: sqlite3.Connection) -> int:
        cursor = c.execute(
            "UPDATE order_emails SET recipient = %s WHERE order_id = %s AND recipient != %s",
            (_ERASED_PLACEHOLDER, order_id, _ERASED_PLACEHOLDER),
        )
        return cursor.rowcount

    if conn is not None:
        return _run(conn)
    with get_db() as owned:
        count = _run(owned)
    logger.info("order_emails_anonymized", order_id=order_id, rows=count)
    return count


def age_out_suppressed_emails(older_than_days: int = 365) -> int:
    """Delete suppressed_emails rows older than `older_than_days`.

    Suppression protects deliverability, but a permanently-retained address list
    is itself PII; aging it out bounds retention. Returns rows deleted.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM suppressed_emails WHERE suppressed_at < datetime('now', %s)",
            (f"-{int(older_than_days)} days",),
        )
        count = cursor.rowcount
    logger.info("suppressed_emails_aged_out", rows=count, older_than_days=older_than_days)
    return count


def anonymize_analytics_subject(
    *,
    session_ids: list[str] | None = None,
    user_ids: list[str] | None = None,
    order_ids: list[str] | None = None,
) -> int:
    """Pseudonymize analytics events linked to an erasure subject."""
    count = analytics_service.anonymize_subject(
        session_ids=session_ids,
        user_ids=user_ids,
        order_ids=order_ids,
    )
    logger.info(
        "analytics_subject_anonymized",
        rows=count,
        session_count=len(session_ids or []),
        user_count=len(user_ids or []),
        order_count=len(order_ids or []),
    )
    return count
