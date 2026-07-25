"""Tests for contact persistence and durable owner notification delivery."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.database import get_db, init_db
from app.email.providers import TransientEmailError
from app.models.contact import ContactRequest
from app.services.contact_service import (
    CONTACT_RATE_LIMIT_PER_HOUR,
    ContactRateLimitExceededError,
    cleanup_old_contact_messages,
    create_contact_message,
    drain_contact_message_emails,
)


class RecordingProvider:
    """In-memory provider double for contact email tests."""

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
        return f"contact-msg-{self.call_count}"


class BlockingProvider:
    """Provider that holds the first send open while another drain races."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.call_count = 0

    def send(self, *, to, subject, body, reply_to=None, tags=None) -> str:
        with self.lock:
            self.call_count += 1
        self.started.set()
        self.release.wait(timeout=2)
        return "contact-blocked-1"


@pytest.fixture()
def db(tmp_path):
    init_db(str(tmp_path / "test.db"))
    yield


def _settings(**overrides) -> Settings:
    base = {
        "environment": "test",
        "email_provider": "console",
        "email_from_address": "orders@theateliermarie.com",
        "email_from_name": "Atelier Marie",
        "email_reply_to": "contacts@theateliermarie.com",
        "admin_notification_email": "contacts@theateliermarie.com",
        "frontend_url": "https://shop.example",
        "jwt_secret": "x" * 40,
        "admin_api_key": "y" * 40,
    }
    base.update(overrides)
    return Settings(**base)


def _request(**overrides) -> ContactRequest:
    data = {
        "name": "Ava Atelier",
        "email": "ava@example.com",
        "message": "Can I order a custom candle?",
        "locale": "en",
    }
    data.update(overrides)
    return ContactRequest(**data)


def test_valid_contact_persists_as_queued(db):
    with get_db() as conn:
        message_id = create_contact_message(conn, _request(), ip_address="203.0.113.5")

    with get_db() as conn:
        row = conn.execute("SELECT * FROM contact_messages WHERE id = ?", (message_id,)).fetchone()

    assert row["name"] == "Ava Atelier"
    assert row["email"] == "ava@example.com"
    assert row["email_status"] == "queued"
    assert row["ip_address"] == "203.0.113.5"


def test_contact_email_is_normalized_before_persisting(db):
    with get_db() as conn:
        message_id = create_contact_message(
            conn, _request(email="AVA@EXAMPLE.COM"), ip_address="203.0.113.5"
        )

    with get_db() as conn:
        row = conn.execute(
            "SELECT email FROM contact_messages WHERE id = ?", (message_id,)
        ).fetchone()

    assert row["email"] == "ava@example.com"


def test_honeypot_is_ignored(db):
    with get_db() as conn:
        message_id = create_contact_message(
            conn, _request(website="https://spam.example"), ip_address="203.0.113.5"
        )
        count = conn.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]

    assert message_id is None
    assert count == 0


def test_rate_limit_counts_recent_accepted_messages(db):
    with get_db() as conn:
        for index in range(CONTACT_RATE_LIMIT_PER_HOUR):
            create_contact_message(
                conn,
                _request(email=f"person{index}@example.com"),
                ip_address="203.0.113.5",
            )

        with pytest.raises(ContactRateLimitExceededError):
            create_contact_message(
                conn,
                _request(email="last@example.com"),
                ip_address="203.0.113.5",
            )


def test_rate_limit_counts_missing_ip_submissions(db):
    with get_db() as conn:
        for index in range(CONTACT_RATE_LIMIT_PER_HOUR):
            create_contact_message(
                conn,
                _request(email=f"person{index}@example.com"),
                ip_address=None,
            )

        with pytest.raises(ContactRateLimitExceededError):
            create_contact_message(conn, _request(email="last@example.com"), ip_address=None)


def test_concurrent_submissions_respect_rate_limit(db):
    start = threading.Barrier(CONTACT_RATE_LIMIT_PER_HOUR * 2)

    def submit(index: int) -> str:
        start.wait(timeout=2)
        try:
            with get_db() as conn:
                create_contact_message(
                    conn,
                    _request(email=f"burst{index}@example.com"),
                    ip_address="203.0.113.77",
                )
            return "created"
        except ContactRateLimitExceededError:
            return "limited"

    with ThreadPoolExecutor(max_workers=CONTACT_RATE_LIMIT_PER_HOUR * 2) as executor:
        results = list(executor.map(submit, range(CONTACT_RATE_LIMIT_PER_HOUR * 2)))

    assert results.count("created") == CONTACT_RATE_LIMIT_PER_HOUR
    assert results.count("limited") == CONTACT_RATE_LIMIT_PER_HOUR
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
    assert count == CONTACT_RATE_LIMIT_PER_HOUR


def test_contact_email_sends_to_admin_with_submitter_reply_to(db):
    with get_db() as conn:
        create_contact_message(conn, _request(locale="en"), ip_address="203.0.113.5")

    provider = RecordingProvider()
    processed = drain_contact_message_emails(provider=provider, settings=_settings())

    assert processed == 1
    assert len(provider.sent) == 1
    assert provider.sent[0]["to"] == "contacts@theateliermarie.com"
    assert provider.sent[0]["subject"] == "New contact message from Ava Atelier"
    assert provider.sent[0]["reply_to"] == "ava@example.com"
    assert provider.sent[0]["tags"] == ["contact_message"]
    assert "Can I order a custom candle?" in provider.sent[0]["body"]
    with get_db() as conn:
        row = conn.execute("SELECT email_status, email_attempts FROM contact_messages").fetchone()
    assert row["email_status"] == "sent"
    assert row["email_attempts"] == 1


def test_contact_email_bg_template_renders(db):
    with get_db() as conn:
        create_contact_message(conn, _request(locale="bg"), ip_address="203.0.113.5")

    provider = RecordingProvider()
    drain_contact_message_emails(provider=provider, settings=_settings())

    assert "Ново съобщение" in provider.sent[0]["subject"]


def test_no_admin_email_configured_skips_without_send(db):
    with get_db() as conn:
        create_contact_message(conn, _request(), ip_address="203.0.113.5")

    provider = RecordingProvider()
    drain_contact_message_emails(provider=provider, settings=_settings(admin_notification_email=""))

    assert provider.sent == []
    with get_db() as conn:
        row = conn.execute("SELECT email_status, email_error FROM contact_messages").fetchone()
    assert row["email_status"] == "skipped_suppressed"
    assert row["email_error"] == "no recipient configured"


def test_transient_failure_stays_retryable(db):
    with get_db() as conn:
        create_contact_message(conn, _request(), ip_address="203.0.113.5")

    provider = RecordingProvider(raise_exc=TransientEmailError("down"))
    drain_contact_message_emails(provider=provider, settings=_settings())

    with get_db() as conn:
        row = conn.execute(
            "SELECT email_status, email_attempts, email_next_attempt_at FROM contact_messages"
        ).fetchone()
    assert row["email_status"] == "failed"
    assert row["email_attempts"] == 1
    assert row["email_next_attempt_at"] is not None


def test_repeated_drains_send_contact_once(db):
    with get_db() as conn:
        create_contact_message(conn, _request(), ip_address="203.0.113.5")

    provider = RecordingProvider()
    drain_contact_message_emails(provider=provider, settings=_settings())
    drain_contact_message_emails(provider=provider, settings=_settings())

    assert provider.call_count == 1
    with get_db() as conn:
        sent_count = conn.execute(
            "SELECT COUNT(*) FROM contact_messages WHERE email_status = 'sent'"
        ).fetchone()[0]
    assert sent_count == 1


def test_concurrent_drains_send_contact_once(db):
    with get_db() as conn:
        create_contact_message(conn, _request(), ip_address="203.0.113.5")

    provider = BlockingProvider()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            drain_contact_message_emails, provider=provider, settings=_settings()
        )
        assert provider.started.wait(timeout=2)
        second = executor.submit(
            drain_contact_message_emails, provider=provider, settings=_settings()
        )
        provider.release.set()
        first.result(timeout=2)
        second.result(timeout=2)

    assert provider.call_count == 1
    with get_db() as conn:
        sent_count = conn.execute(
            "SELECT COUNT(*) FROM contact_messages WHERE email_status = 'sent'"
        ).fetchone()[0]
    assert sent_count == 1


def test_cleanup_old_contact_messages_removes_only_expired_rows(db):
    old_created = (datetime.now(UTC) - timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S")
    recent_created = (datetime.now(UTC) - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO contact_messages (name, email, message, locale, created_at)
            VALUES ('Old', 'old@example.com', 'old', 'en', ?)
            """,
            (old_created,),
        )
        conn.execute(
            """
            INSERT INTO contact_messages (name, email, message, locale, created_at)
            VALUES ('Recent', 'recent@example.com', 'recent', 'en', ?)
            """,
            (recent_created,),
        )

    assert cleanup_old_contact_messages(retention_days=365) == 1
    with get_db() as conn:
        emails = [row["email"] for row in conn.execute("SELECT email FROM contact_messages")]
    assert emails == ["recent@example.com"]
