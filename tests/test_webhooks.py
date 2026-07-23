"""Tests for ZeptoMail webhook handling: signature verification, replay
rejection, raw-body verification, suppression, idempotency; plus GDPR helpers.
"""

import hashlib
import hmac
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_db, init_db
from app.services.gdpr_service import age_out_suppressed_emails, anonymize_order_emails
from app.services.webhook_service import (
    WebhookVerificationError,
    handle_webhook_event,
    verify_signature,
)

_SECRET = "webhook-secret-key"  # pragma: allowlist secret


def _sign(body: bytes, secret: str = _SECRET, ts: int | None = None) -> str:
    ts = ts if ts is not None else int(time.time())
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"ts={ts}, s={sig}, s-algorithm=HMAC-SHA256"


@pytest.fixture()
def db(tmp_path):
    init_db(str(tmp_path / "test.db"))
    yield


class TestVerifySignature:
    def test_valid_signature_passes(self):
        body = b'{"event_name":"hard_bounce"}'
        verify_signature(body, _sign(body), _SECRET)  # no raise

    def test_missing_header_rejected(self):
        with pytest.raises(WebhookVerificationError):
            verify_signature(b"{}", None, _SECRET)

    def test_no_secret_rejected(self):
        body = b"{}"
        with pytest.raises(WebhookVerificationError):
            verify_signature(body, _sign(body), "")

    def test_tampered_body_rejected(self):
        body = b'{"event_name":"hard_bounce"}'
        header = _sign(body)
        with pytest.raises(WebhookVerificationError):
            verify_signature(b'{"event_name":"tampered"}', header, _SECRET)

    def test_stale_timestamp_rejected(self):
        body = b"{}"
        header = _sign(body, ts=int(time.time()) - 10_000)
        with pytest.raises(WebhookVerificationError, match="stale"):
            verify_signature(body, header, _SECRET)

    def test_bad_algorithm_rejected(self):
        body = b"{}"
        sig = hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()
        with pytest.raises(WebhookVerificationError):
            verify_signature(body, f"ts={int(time.time())}, s={sig}, s-algorithm=MD5", _SECRET)


class TestHandleEvent:
    def test_hard_bounce_suppresses(self, db):
        handle_webhook_event(
            {"event_name": "hard_bounce", "data": [{"bounced_recipient": "bad@example.com"}]}
        )
        with get_db() as conn:
            row = conn.execute(
                "SELECT reason FROM suppressed_emails WHERE email = ?", ("bad@example.com",)
            ).fetchone()
        assert row is not None
        assert row["reason"] == "hard_bounce"

    def test_complaint_suppresses(self, db):
        handle_webhook_event(
            {"event_name": "fbl_complaint", "email_address": {"address": "spam@example.com"}}
        )
        with get_db() as conn:
            row = conn.execute(
                "SELECT 1 FROM suppressed_emails WHERE email = ?", ("spam@example.com",)
            ).fetchone()
        assert row is not None

    def test_soft_bounce_not_suppressed(self, db):
        result = handle_webhook_event(
            {"event_name": "soft_bounce", "recipient": "temp@example.com"}
        )
        assert result["status"] == "logged"
        with get_db() as conn:
            row = conn.execute(
                "SELECT 1 FROM suppressed_emails WHERE email = ?", ("temp@example.com",)
            ).fetchone()
        assert row is None

    def test_duplicate_bounce_idempotent(self, db):
        payload = {"event_name": "hard_bounce", "recipient": "dup@example.com"}
        handle_webhook_event(payload)
        handle_webhook_event(payload)  # no error, no duplicate row
        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM suppressed_emails WHERE email = ?", ("dup@example.com",)
            ).fetchone()[0]
        assert count == 1


class TestGdprHelpers:
    def test_anonymize_order_emails(self, db):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                "VALUES ('o1', 's1', 'pending', 100, 'x@e.com')"
            )
            conn.execute(
                "INSERT INTO order_emails (order_id, event, recipient, status) "
                "VALUES ('o1', 'placed', 'x@e.com', 'sent')"
            )
        count = anonymize_order_emails("o1")
        assert count == 1
        with get_db() as conn:
            recipient = conn.execute(
                "SELECT recipient FROM order_emails WHERE order_id = 'o1'"
            ).fetchone()[0]
        assert recipient == "[erased]"

    def test_age_out_suppressed(self, db):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO suppressed_emails (email, reason, suppressed_at) "
                "VALUES ('old@e.com', 'hard_bounce', datetime('now', '-400 days'))"
            )
            conn.execute(
                "INSERT INTO suppressed_emails (email, reason) VALUES ('new@e.com', 'hard_bounce')"
            )
        deleted = age_out_suppressed_emails(older_than_days=365)
        assert deleted == 1
        with get_db() as conn:
            remaining = conn.execute("SELECT email FROM suppressed_emails").fetchall()
        emails = {r["email"] for r in remaining}
        assert emails == {"new@e.com"}


@pytest.mark.integration
class TestWebhookRoute:
    @pytest.fixture()
    async def webhook_client(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "wh.db")
        monkeypatch.setenv("DATABASE_PATH", db_path)
        monkeypatch.setenv("ZEPTOMAIL_WEBHOOK_AUTH_KEY", _SECRET)
        monkeypatch.setenv("ADMIN_API_KEY", "z" * 40)
        get_settings.cache_clear()
        init_db(db_path)
        from app.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
        get_settings.cache_clear()

    async def test_valid_webhook_suppresses(self, webhook_client):
        payload = {"event_name": "hard_bounce", "recipient": "bounce@example.com"}
        body = json.dumps(payload).encode("utf-8")
        resp = await webhook_client.post(
            "/v1/webhooks/zeptomail",
            content=body,
            headers={"producer-signature": _sign(body), "content-type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "suppressed"

    async def test_invalid_signature_401(self, webhook_client):
        body = json.dumps({"event_name": "hard_bounce"}).encode("utf-8")
        resp = await webhook_client.post(
            "/v1/webhooks/zeptomail",
            content=body,
            headers={"producer-signature": "ts=1, s=deadbeef, s-algorithm=HMAC-SHA256"},
        )
        assert resp.status_code == 401

    async def test_stale_timestamp_401(self, webhook_client):
        body = json.dumps({"event_name": "hard_bounce"}).encode("utf-8")
        header = _sign(body, ts=int(time.time()) - 10_000)
        resp = await webhook_client.post(
            "/v1/webhooks/zeptomail",
            content=body,
            headers={"producer-signature": header},
        )
        assert resp.status_code == 401

    async def test_no_session_cookie_set(self, webhook_client):
        # Path is in session_skip_paths — machine-to-machine, no cookie issued.
        body = json.dumps({"event_name": "soft_bounce"}).encode("utf-8")
        resp = await webhook_client.post(
            "/v1/webhooks/zeptomail",
            content=body,
            headers={"producer-signature": _sign(body)},
        )
        assert resp.status_code == 200
        assert "set-cookie" not in {k.lower() for k in resp.headers}
