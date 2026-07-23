"""Tests for email providers: console (log output) and ZeptoMail (mocked HTTP)."""

import httpx
import pytest
import structlog.testing

from app.config import Settings
from app.email.providers import (
    PermanentEmailError,
    TransientEmailError,
    get_email_provider,
)
from app.email.providers.console_provider import ConsoleProvider
from app.email.providers.zeptomail_provider import (
    ZeptoMailProvider,
    decode_encoded_word,
    encoded_word_subject,
)


def _settings(**overrides) -> Settings:
    base = {
        "environment": "test",
        "email_provider": "console",
        "email_from_address": "orders@theateliermarie.com",
        "email_from_name": "Atelier Marie",
        # Satisfy production validation when a test flips environment=production.
        "jwt_secret": "x" * 40,
        "admin_api_key": "y" * 40,
    }
    base.update(overrides)
    return Settings(**base)


class TestConsoleProvider:
    def test_logs_full_body_in_dev(self):
        provider = ConsoleProvider(_settings(environment="development"))
        with structlog.testing.capture_logs() as logs:
            result = provider.send(
                to="buyer@example.com",
                subject="Hello",
                body="Body text",
                reply_to="contacts@theateliermarie.com",
            )
        assert result is None
        entry = next(e for e in logs if e["event"] == "email_console_send")
        assert entry["to"] == "buyer@example.com"
        assert entry["subject"] == "Hello"
        assert entry["body"] == "Body text"

    def test_redacts_in_production(self):
        provider = ConsoleProvider(_settings(environment="production"))
        with structlog.testing.capture_logs() as logs:
            provider.send(to="buyer@example.com", subject="Hi", body="secret body")
        entry = next(e for e in logs if e["event"] == "email_console_send")
        assert entry["to"] != "buyer@example.com"
        assert "buyer" not in entry["to"]
        assert "example.com" in entry["to"]  # domain kept
        assert "body" not in entry  # body omitted in production


class TestFactory:
    def test_console_by_default(self):
        assert isinstance(get_email_provider(_settings()), ConsoleProvider)

    def test_zeptomail_when_configured(self):
        provider = get_email_provider(_settings(email_provider="zeptomail", email_api_key="tok"))
        assert isinstance(provider, ZeptoMailProvider)


class TestZeptoMailProvider:
    def _provider(self) -> ZeptoMailProvider:
        return ZeptoMailProvider(
            _settings(email_provider="zeptomail", email_api_key="tok")  # pragma: allowlist secret
        )

    def test_success_returns_message_id(self, monkeypatch):
        captured = {}

        def fake_post(url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return httpx.Response(201, json={"data": [{"message_id": "abc-123"}]})

        monkeypatch.setattr(httpx, "post", fake_post)
        result = self._provider().send(to="b@e.com", subject="S", body="B", reply_to="r@e.com")
        assert result == "abc-123"
        # EU host, tracking disabled, auth header present.
        assert captured["url"].endswith(".eu/v1.1/email")
        assert captured["json"]["track_opens"] is False
        assert captured["json"]["track_clicks"] is False
        assert captured["json"]["reply_to"][0]["address"] == "r@e.com"
        assert captured["headers"]["Authorization"].startswith("Zoho-enczapikey ")

    def test_no_list_unsubscribe_header(self, monkeypatch):
        captured = {}

        def fake_post(url, json, headers, timeout):
            captured["json"] = json
            return httpx.Response(201, json={"data": [{}]})

        monkeypatch.setattr(httpx, "post", fake_post)
        self._provider().send(to="b@e.com", subject="S", body="B")
        # No unsubscribe anywhere in the payload.
        assert "list-unsubscribe" not in str(captured["json"]).lower()

    def test_5xx_is_transient(self, monkeypatch):
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: httpx.Response(503, text="unavailable"))
        with pytest.raises(TransientEmailError):
            self._provider().send(to="b@e.com", subject="S", body="B")

    def test_timeout_is_transient(self, monkeypatch):
        def boom(*a, **kw):
            raise httpx.TimeoutException("timed out")

        monkeypatch.setattr(httpx, "post", boom)
        with pytest.raises(TransientEmailError):
            self._provider().send(to="b@e.com", subject="S", body="B")

    def test_4xx_is_permanent(self, monkeypatch):
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: httpx.Response(400, text="bad request"))
        with pytest.raises(PermanentEmailError):
            self._provider().send(to="b@e.com", subject="S", body="B")

    def test_quota_exhausted_flagged(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "post", lambda *a, **kw: httpx.Response(400, text="Insufficient credit")
        )
        with pytest.raises(PermanentEmailError) as exc:
            self._provider().send(to="b@e.com", subject="S", body="B")
        assert exc.value.quota_exhausted is True

    def test_missing_key_is_permanent(self):
        provider = ZeptoMailProvider(_settings(email_provider="zeptomail", email_api_key=""))
        with pytest.raises(PermanentEmailError):
            provider.send(to="b@e.com", subject="S", body="B")


class TestCyrillicSubjectEncoding:
    """11.3 / Decision 18: Cyrillic subjects round-trip as RFC 2047 encoded-words."""

    def test_round_trip(self):
        original = "Вашата поръчка №1234abcd от Atelier Marie"
        encoded = encoded_word_subject(original)
        # Encoded-word form, not raw bytes.
        assert "=?" in encoded and "?=" in encoded
        assert decode_encoded_word(encoded) == original

    def test_ascii_subject_unchanged_after_round_trip(self):
        original = "Your Atelier Marie order #1234abcd"
        assert decode_encoded_word(encoded_word_subject(original)) == original
