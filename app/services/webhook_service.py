"""ZeptoMail bounce/complaint webhook handling (email-deliverability Decision 15).

Consumes `hard_bounce`, `soft_bounce`, and `fbl_complaint` events. Hard bounces
and complaints suppress the recipient so the store stops mailing a known-bad
address; soft bounces are logged only. Signature verification uses ZeptoMail's
`producer-signature` scheme (HMAC-SHA256 over the raw body) with a timestamp
tolerance to reject replays.
"""

import hashlib
import hmac
import time

import structlog

from app.database import get_db
from app.email.redaction import redact_recipient

logger = structlog.get_logger(__name__)

# Reject webhooks whose signed timestamp is older/newer than this (replay guard).
_TIMESTAMP_TOLERANCE_SECONDS = 300
_SUPPRESSING_EVENTS = {"hard_bounce", "fbl_complaint"}


class WebhookVerificationError(Exception):
    """Raised when a webhook signature/timestamp fails verification."""


def _parse_signature_header(header: str) -> dict[str, str]:
    """Parse ZeptoMail's `producer-signature` header into its parts.

    The header carries `ts`, `s` (the HMAC), and `s-algorithm` as delimited
    key=value pairs (comma- or semicolon-separated). Parsing is lenient about
    the delimiter and surrounding whitespace.
    """
    parts: dict[str, str] = {}
    for chunk in header.replace(";", ",").split(","):
        key, _, value = chunk.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            parts[key] = value
    return parts


def verify_signature(raw_body: bytes, header: str | None, secret: str) -> None:
    """Verify the `producer-signature` header over the raw request body.

    Raises WebhookVerificationError on any failure: missing header/secret,
    unknown algorithm, stale timestamp (replay), or HMAC mismatch. Uses a
    constant-time comparison.
    """
    if not secret:
        raise WebhookVerificationError("webhook auth key not configured")
    if not header:
        raise WebhookVerificationError("missing producer-signature header")

    parts = _parse_signature_header(header)
    ts = parts.get("ts")
    signature = parts.get("s")
    algorithm = parts.get("s-algorithm", "")

    if not ts or not signature:
        raise WebhookVerificationError("signature header missing ts or s")
    if algorithm.upper() not in ("HMAC-SHA256", "HMACSHA256", "SHA256"):
        raise WebhookVerificationError(f"unsupported signature algorithm: {algorithm}")

    try:
        ts_int = int(ts)
    except ValueError as exc:
        raise WebhookVerificationError("invalid ts") from exc

    if abs(int(time.time()) - ts_int) > _TIMESTAMP_TOLERANCE_SECONDS:
        raise WebhookVerificationError("stale timestamp (possible replay)")

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise WebhookVerificationError("signature mismatch")


def _find_recipients(payload: object) -> list[str]:
    """Best-effort recursive extraction of recipient addresses from a payload.

    ZeptoMail's exact bounce shape varies; we search common address-bearing keys
    ('address', 'email', 'recipient', 'bounced_recipient') at any depth.
    """
    found: list[str] = []
    address_keys = {"address", "email", "recipient", "bounced_recipient", "email_address"}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in address_keys and isinstance(value, str) and "@" in value:
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    # De-duplicate, preserve order.
    return list(dict.fromkeys(found))


def _event_type(payload: dict) -> str | None:
    for key in ("event_name", "event", "type", "event_type"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def suppress_email(email: str, reason: str) -> None:
    """Record an address as undeliverable. Idempotent (duplicate bounce is a
    no-op), so redelivered webhooks don't error (email-deliverability spec)."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO suppressed_emails (email, reason) VALUES (?, ?)",
            (email, reason),
        )


def handle_webhook_event(payload: dict) -> dict:
    """Process a verified webhook payload. Returns a small status summary.

    Suppresses recipients on hard bounce / complaint; logs soft bounces.
    """
    event = _event_type(payload)
    recipients = _find_recipients(payload)

    if event in _SUPPRESSING_EVENTS:
        for email in recipients:
            suppress_email(email, event)
            logger.info(
                "email_recipient_suppressed",
                webhook_event=event,
                recipient=redact_recipient(email),
            )
        return {"status": "suppressed", "event": event, "count": len(recipients)}

    if event == "soft_bounce":
        for email in recipients:
            logger.info(
                "email_soft_bounce",
                recipient=redact_recipient(email),
            )
        return {"status": "logged", "event": event, "count": len(recipients)}

    logger.info("email_webhook_ignored", webhook_event=event)
    return {"status": "ignored", "event": event}
