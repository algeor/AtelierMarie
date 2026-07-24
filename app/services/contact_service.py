"""Contact form persistence and durable owner notification delivery."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TypedDict

import structlog

from app.config import Settings, get_settings
from app.constants import SQLITE_DATETIME_FORMAT
from app.database import get_db
from app.email.providers import (
    EmailProvider,
    PermanentEmailError,
    TransientEmailError,
    get_email_provider,
)
from app.email.redaction import redact_recipient
from app.email.renderer import TemplateMissingError, render_template
from app.models.contact import ContactRequest

logger = structlog.get_logger(__name__)

CONTACT_EMAIL_EVENT = "contact_message"
CONTACT_RATE_LIMIT_PER_HOUR = 5
MAX_CONTACT_EMAIL_ATTEMPTS = 5
CONTACT_CLAIM_LEASE_SECONDS = 300
_BACKOFF_BASE_SECONDS = 30
_SWEEP_BATCH_LIMIT = 50


class ContactMessageRow(TypedDict):
    """Contact row fields needed for email delivery."""

    id: int
    name: str
    email: str
    message: str
    locale: str
    ip_address: str | None
    email_attempts: int
    created_at: str


class ContactRateLimitExceededError(Exception):
    """Raised when an IP exceeds the accepted contact submission limit."""


def _now() -> datetime:
    return datetime.now(UTC)


def _now_s() -> str:
    return _now().strftime(SQLITE_DATETIME_FORMAT)


def _backoff_next_attempt(attempts: int) -> str:
    delay = _BACKOFF_BASE_SECONDS * (2 ** max(0, attempts - 1))
    return (_now() + timedelta(seconds=delay)).strftime(SQLITE_DATETIME_FORMAT)


def is_contact_rate_limited(
    conn: sqlite3.Connection,
    ip_address: str | None,
    *,
    limit: int = CONTACT_RATE_LIMIT_PER_HOUR,
) -> bool:
    """Return whether this IP has reached the rolling one-hour contact limit."""
    if not ip_address:
        return False
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM contact_messages
        WHERE ip_address = ?
          AND created_at >= datetime('now', '-1 hour')
        """,
        (ip_address,),
    ).fetchone()
    return int(row["count"] if row else 0) >= limit


def create_contact_message(
    conn: sqlite3.Connection,
    body: ContactRequest,
    *,
    ip_address: str | None,
) -> int | None:
    """Persist a contact message as queued email work.

    Returns the inserted message id. Honeypot submissions return None and are
    intentionally not persisted.
    """
    if body.website:
        return None
    if is_contact_rate_limited(conn, ip_address):
        raise ContactRateLimitExceededError("Too many requests. Please try again later.")

    cursor = conn.execute(
        """
        INSERT INTO contact_messages (name, email, message, locale, ip_address, email_status)
        VALUES (?, ?, ?, ?, ?, 'queued')
        """,
        (body.name, str(body.email), body.message, body.locale, ip_address),
    )
    return int(cursor.lastrowid)


def _build_contact_context(row: ContactMessageRow) -> dict:
    return {
        "message_id": row["id"],
        "submitter_name": row["name"],
        "submitter_email": row["email"],
        "message": row["message"],
        "locale": row["locale"],
        "ip_address": row["ip_address"],
        "created_at": row["created_at"],
    }


def _claim_contact_row(row_id: int) -> ContactMessageRow | None:
    """Atomically claim one contact row for this drain tick."""
    now_s = _now_s()
    lease_s = (_now() + timedelta(seconds=CONTACT_CLAIM_LEASE_SECONDS)).strftime(
        SQLITE_DATETIME_FORMAT
    )

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                """
                SELECT id, name, email, message, locale, ip_address, email_attempts, created_at,
                       email_status, email_next_attempt_at, email_claimed_until
                FROM contact_messages
                WHERE id = ?
                """,
                (row_id,),
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None

            status = row["email_status"]
            next_attempt_at = row["email_next_attempt_at"]
            claimed_until = row["email_claimed_until"]
            is_retryable = status in {"queued", "failed"} and (
                next_attempt_at is None or next_attempt_at <= now_s
            )
            is_expired_claim = status == "in_flight" and (
                claimed_until is None or claimed_until < now_s
            )
            if not (is_retryable or is_expired_claim):
                conn.execute("COMMIT")
                return None

            conn.execute(
                """
                UPDATE contact_messages
                SET email_status = 'in_flight', email_claimed_until = ?, email_error = NULL
                WHERE id = ?
                """,
                (lease_s, row_id),
            )
            conn.execute("COMMIT")
            return {
                "id": int(row["id"]),
                "name": row["name"],
                "email": row["email"],
                "message": row["message"],
                "locale": row["locale"],
                "ip_address": row["ip_address"],
                "email_attempts": int(row["email_attempts"]),
                "created_at": row["created_at"],
            }
        except Exception:
            conn.execute("ROLLBACK")
            raise


def _mark_contact_email(
    row_id: int,
    status: str,
    *,
    attempts: int | None = None,
    error: str | None = None,
    next_attempt_at: str | None = None,
    sent_at: str | None = None,
) -> None:
    fields = [
        "email_status = ?",
        "email_error = ?",
        "email_next_attempt_at = ?",
        "email_claimed_until = NULL",
    ]
    params: list[object] = [status, error, next_attempt_at]
    if attempts is not None:
        fields.append("email_attempts = ?")
        params.append(attempts)
    if sent_at is not None:
        fields.append("email_sent_at = ?")
        params.append(sent_at)
    params.append(row_id)

    with get_db() as conn:
        conn.execute(
            f"UPDATE contact_messages SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
            params,
        )


def _process_contact_row(
    row_id: int,
    *,
    provider: EmailProvider,
    settings: Settings,
) -> None:
    row = _claim_contact_row(row_id)
    if row is None:
        return

    log = logger.bind(contact_message_id=row_id, email_event=CONTACT_EMAIL_EVENT)
    recipient = settings.admin_notification_email
    if not recipient:
        _mark_contact_email(row_id, "skipped_suppressed", error="no recipient configured")
        log.info("contact_email_skipped_no_recipient")
        return

    try:
        subject, body = render_template(
            CONTACT_EMAIL_EVENT,
            row["locale"],
            _build_contact_context(row),
        )
    except TemplateMissingError as exc:
        attempts = row["email_attempts"] + 1
        _mark_contact_email(row_id, "failed_permanent", attempts=attempts, error=str(exc))
        log.error("contact_email_template_missing", error=str(exc))
        return

    try:
        message_id = provider.send(
            to=recipient,
            subject=subject,
            body=body,
            reply_to=row["email"],
            tags=[CONTACT_EMAIL_EVENT],
        )
    except TransientEmailError as exc:
        attempts = row["email_attempts"] + 1
        if attempts >= MAX_CONTACT_EMAIL_ATTEMPTS:
            _mark_contact_email(row_id, "failed_permanent", attempts=attempts, error=str(exc))
            log.error("contact_email_failed_permanent", error=str(exc))
        else:
            _mark_contact_email(
                row_id,
                "failed",
                attempts=attempts,
                error=str(exc),
                next_attempt_at=_backoff_next_attempt(attempts),
            )
            log.warning("contact_email_transient_failure", attempts=attempts, error=str(exc))
        return
    except PermanentEmailError as exc:
        attempts = row["email_attempts"] + 1
        _mark_contact_email(row_id, "failed_permanent", attempts=attempts, error=str(exc))
        log.error("contact_email_permanent_failure", error=str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - email failure must not kill drain loop
        attempts = row["email_attempts"] + 1
        if attempts >= MAX_CONTACT_EMAIL_ATTEMPTS:
            _mark_contact_email(row_id, "failed_permanent", attempts=attempts, error=str(exc))
            log.error("contact_email_unexpected_failed_permanent", error=str(exc))
        else:
            _mark_contact_email(
                row_id,
                "failed",
                attempts=attempts,
                error=str(exc),
                next_attempt_at=_backoff_next_attempt(attempts),
            )
            log.warning("contact_email_unexpected_failure", attempts=attempts, error=str(exc))
        return

    _mark_contact_email(
        row_id,
        "sent",
        attempts=row["email_attempts"] + 1,
        error=message_id,
        sent_at=_now_s(),
    )
    log.info("contact_email_sent", recipient=redact_recipient(recipient), message_id=message_id)


def drain_contact_message_emails(
    *,
    provider: EmailProvider | None = None,
    settings: Settings | None = None,
) -> int:
    """Process eligible contact notification rows. Returns selected row count."""
    settings = settings or get_settings()
    provider = provider or get_email_provider(settings)
    now_s = _now_s()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id FROM contact_messages
            WHERE email_attempts < ?
              AND (
                (email_status IN ('queued', 'failed')
                 AND (email_next_attempt_at IS NULL OR email_next_attempt_at <= ?))
                OR (email_status = 'in_flight'
                    AND (email_claimed_until IS NULL OR email_claimed_until < ?))
              )
            ORDER BY id
            LIMIT ?
            """,
            (MAX_CONTACT_EMAIL_ATTEMPTS, now_s, now_s, _SWEEP_BATCH_LIMIT),
        ).fetchall()
        row_ids = [int(r["id"]) for r in rows]

    for row_id in row_ids:
        try:
            _process_contact_row(row_id, provider=provider, settings=settings)
        except Exception:
            logger.exception("contact_email_row_crashed", contact_message_id=row_id)

    return len(row_ids)
