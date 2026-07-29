"""Tests for the email service: context building, send path, idempotency,
retry/backoff, locale-from-order, and audit logging.

Uses an in-memory RecordingProvider double (no network) and the durable-outbox
drain entry point.
"""

import sqlite3
import uuid
from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.database import get_db, init_db
from app.email.providers import PermanentEmailError, TransientEmailError
from app.services.email_service import (
    MAX_ATTEMPTS,
    drain_email_outbox,
    format_price,
    queue_order_email,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


class RecordingProvider:
    """In-memory EmailProvider double. Records sends; can be told to fail."""

    def __init__(self, *, raise_exc: Exception | None = None) -> None:
        self.sent: list[dict] = []
        self.raise_exc = raise_exc
        self.call_count = 0

    def send(self, *, to, subject, body, reply_to=None, tags=None) -> str | None:
        self.call_count += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        self.sent.append(
            {"to": to, "subject": subject, "body": body, "reply_to": reply_to, "tags": tags}
        )
        return f"msg-{self.call_count}"


@pytest.fixture()
def db(tmp_path):
    """Fresh initialized DB (sets the get_db module path)."""
    init_db(str(tmp_path / "test.db"))
    yield


def _settings(**overrides) -> Settings:
    base = {
        "environment": "test",
        "email_provider": "console",
        "email_from_address": "orders@theateliermarie.com",
        "email_from_name": "Atelier Marie",
        "email_reply_to": "contacts@theateliermarie.com",
        "admin_notification_email": "owner@theateliermarie.com",
        "frontend_url": "https://shop.example",
        "jwt_secret": "x" * 40,
        "admin_api_key": "y" * 40,
    }
    base.update(overrides)
    return Settings(**base)


def _make_order(
    conn: sqlite3.Connection,
    *,
    locale: str = "en",
    email: str = "buyer@example.com",
    name: str | None = "Ben & Co",
    status: str = "pending",
    tracking_carrier: str | None = None,
    tracking_number: str | None = None,
    tracking_url: str | None = None,
) -> str:
    order_id = str(uuid.uuid4())
    now = datetime.now(UTC).strftime(_DT_FMT)
    conn.execute(
        """INSERT INTO orders (id, session_id, status, total_cents, customer_email,
               customer_name, locale, tracking_carrier, tracking_number, tracking_url,
               created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            order_id,
            "sess-1",
            status,
            8500,
            email,
            name,
            locale,
            tracking_carrier,
            tracking_number,
            tracking_url,
            now,
            now,
        ),
    )
    conn.execute(
        "INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity) "
        "VALUES (?, ?, ?, ?, ?)",
        (order_id, "lavender-dream", "Lavender Dream", 2500, 2),
    )
    return order_id


class TestFormatPrice:
    def test_en(self):
        assert format_price(4500, "en") == "€45.00"

    def test_bg(self):
        assert format_price(4500, "bg") == "45.00 лв"


class TestSendPath:
    def test_queued_placed_email_sends(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        provider = RecordingProvider()
        processed = drain_email_outbox(provider=provider, settings=_settings())

        assert processed == 1
        assert len(provider.sent) == 1
        sent = provider.sent[0]
        assert sent["to"] == "buyer@example.com"
        assert sent["reply_to"] == "contacts@theateliermarie.com"
        assert "Lavender Dream" in sent["body"]
        assert "https://shop.example/en/terms" in sent["body"]
        assert "https://shop.example/en/privacy" in sent["body"]
        assert "contacts@theateliermarie.com" in sent["body"]
        # No List-Unsubscribe anywhere.
        assert "list-unsubscribe" not in str(sent).lower()

        with get_db() as conn:
            row = conn.execute(
                "SELECT status FROM order_emails WHERE order_id = ? AND event = 'placed'",
                (order_id,),
            ).fetchone()
        assert row["status"] == "sent"

    def test_locale_read_from_order_not_session(self, db):
        # Order locale bg; the "session" (admin) is irrelevant — email must be BG.
        with get_db() as conn:
            order_id = _make_order(conn, locale="bg")
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        provider = RecordingProvider()
        drain_email_outbox(provider=provider, settings=_settings())
        assert "поръчка" in provider.sent[0]["subject"].lower()
        assert "https://shop.example/bg/terms" in provider.sent[0]["body"]
        assert "https://shop.example/bg/privacy" in provider.sent[0]["body"]

    def test_admin_alert_uses_admin_address(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "admin_new_order", "owner@theateliermarie.com")
        provider = RecordingProvider()
        drain_email_outbox(provider=provider, settings=_settings())
        assert provider.sent[0]["to"] == "owner@theateliermarie.com"

    def test_no_admin_email_configured_skips(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "admin_new_order", "")
        provider = RecordingProvider()
        drain_email_outbox(provider=provider, settings=_settings(admin_notification_email=""))
        assert provider.sent == []
        with get_db() as conn:
            row = conn.execute(
                "SELECT status FROM order_emails WHERE order_id = ? AND event = 'admin_new_order'",
                (order_id,),
            ).fetchone()
        assert row["status"] == "skipped_suppressed"


class TestIdempotency:
    def test_concurrent_drains_send_once(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        # Simulate two workers by draining twice; the claim + UNIQUE index
        # guarantee a single provider call and one 'sent' row.
        provider = RecordingProvider()
        drain_email_outbox(provider=provider, settings=_settings())
        drain_email_outbox(provider=provider, settings=_settings())

        assert provider.call_count == 1
        with get_db() as conn:
            sent = conn.execute(
                "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND status = 'sent'",
                (order_id,),
            ).fetchone()[0]
        assert sent == 1

    def test_live_claim_leaves_outbox_row_retryable(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")
            conn.execute(
                """
                INSERT INTO order_email_send_claims (
                    order_id, event, status, lease_expires_at, updated_at
                ) VALUES (?, 'placed', 'in_flight', datetime('now', '+5 minutes'), datetime('now'))
                """,
                (order_id,),
            )

        provider = RecordingProvider()
        processed = drain_email_outbox(provider=provider, settings=_settings())

        assert processed == 1
        assert provider.call_count == 0
        with get_db() as conn:
            row = conn.execute(
                "SELECT status, reason FROM order_emails WHERE order_id = ? AND event = 'placed'",
                (order_id,),
            ).fetchone()
        assert row["status"] == "queued"
        assert row["reason"] is None

    def test_distinct_events_each_send(self, db):
        with get_db() as conn:
            order_id = _make_order(conn, tracking_carrier="speedy", tracking_number="77")
            queue_order_email(conn, order_id, "placed", "buyer@example.com")
            queue_order_email(conn, order_id, "shipped", "buyer@example.com")
            queue_order_email(conn, order_id, "delivered", "buyer@example.com")

        provider = RecordingProvider()
        drain_email_outbox(provider=provider, settings=_settings())
        assert provider.call_count == 3


class TestRetry:
    def test_transient_error_stays_retryable(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        provider = RecordingProvider(raise_exc=TransientEmailError("boom"))
        drain_email_outbox(provider=provider, settings=_settings())

        with get_db() as conn:
            row = conn.execute(
                "SELECT status, attempts, next_attempt_at FROM order_emails WHERE order_id = ?",
                (order_id,),
            ).fetchone()
        assert row["status"] == "failed"
        assert row["attempts"] == 1
        assert row["next_attempt_at"] is not None

    def test_provider_recovers_eventually_sends_once(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        # Down for a tick.
        drain_email_outbox(
            provider=RecordingProvider(raise_exc=TransientEmailError("down")),
            settings=_settings(),
        )
        # Clear the backoff gate so the row is eligible again.
        with get_db() as conn:
            conn.execute(
                "UPDATE order_emails SET next_attempt_at = NULL WHERE order_id = ?", (order_id,)
            )

        good = RecordingProvider()
        drain_email_outbox(provider=good, settings=_settings())
        drain_email_outbox(provider=good, settings=_settings())
        assert good.call_count == 1
        with get_db() as conn:
            sent = conn.execute(
                "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND status = 'sent'",
                (order_id,),
            ).fetchone()[0]
        assert sent == 1

    def test_max_attempts_marks_failed_permanent(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        provider = RecordingProvider(raise_exc=TransientEmailError("always down"))
        # Drain repeatedly, clearing the backoff gate each round.
        for _ in range(MAX_ATTEMPTS + 1):
            drain_email_outbox(provider=provider, settings=_settings())
            with get_db() as conn:
                conn.execute(
                    "UPDATE order_emails SET next_attempt_at = NULL WHERE order_id = ?",
                    (order_id,),
                )

        with get_db() as conn:
            row = conn.execute(
                "SELECT status, attempts FROM order_emails WHERE order_id = ?",
                (order_id,),
            ).fetchone()
        assert row["status"] == "failed_permanent"
        assert row["attempts"] >= MAX_ATTEMPTS

    def test_permanent_error_immediately_terminal(self, db):
        with get_db() as conn:
            order_id = _make_order(conn)
            queue_order_email(conn, order_id, "placed", "buyer@example.com")

        provider = RecordingProvider(raise_exc=PermanentEmailError("bad request"))
        drain_email_outbox(provider=provider, settings=_settings())

        with get_db() as conn:
            row = conn.execute(
                "SELECT status FROM order_emails WHERE order_id = ?", (order_id,)
            ).fetchone()
        assert row["status"] == "failed_permanent"


class TestSuppression:
    def test_suppressed_recipient_skipped(self, db):
        with get_db() as conn:
            order_id = _make_order(conn, email="bad@example.com")
            conn.execute(
                "INSERT INTO suppressed_emails (email, reason) VALUES (?, 'hard_bounce')",
                ("bad@example.com",),
            )
            queue_order_email(conn, order_id, "placed", "bad@example.com")

        provider = RecordingProvider()
        drain_email_outbox(provider=provider, settings=_settings())
        assert provider.sent == []
        with get_db() as conn:
            row = conn.execute(
                "SELECT status FROM order_emails WHERE order_id = ?", (order_id,)
            ).fetchone()
        assert row["status"] == "skipped_suppressed"
