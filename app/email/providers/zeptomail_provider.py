"""ZeptoMail (EU) transactional email provider — HTTP API via httpx.

Sends one plain-text email per call as a stateless HTTPS POST (Decision 24:
API over SMTP). Open/click tracking is disabled on every send (Decision 13),
and no List-Unsubscribe header is attached (transactional mail — Decision 18).

ZeptoMail has no send-level idempotency key; duplicate suppression is entirely
the DB claim + `order_emails` UNIQUE index (Decision 14), so nothing here.
"""

from email.header import Header, decode_header

import httpx
import structlog

from app.config import Settings
from app.email.providers import PermanentEmailError, TransientEmailError

logger = structlog.get_logger(__name__)

# EU data center host — keeps sending data in-region (GDPR, Decision 1).
_ZEPTOMAIL_API_URL = "https://api.zeptomail.eu/v1.1/email"
_TIMEOUT_SECONDS = 10.0


def encoded_word_subject(subject: str) -> str:
    """Return an RFC 2047 encoded-word form of a (possibly Cyrillic) subject.

    The ZeptoMail API encodes headers itself when we hand it a UTF-8 JSON
    string, so the live send path passes the raw subject. This helper exists so
    the encoding is testable (Decision 18) and is reused if the SMTP fallback
    provider is ever adopted (headers there are our responsibility).
    """
    return Header(subject, "utf-8").encode()


def decode_encoded_word(encoded: str) -> str:
    """Inverse of `encoded_word_subject` — used by the round-trip test."""
    parts = decode_header(encoded)
    return "".join(
        fragment.decode(charset or "utf-8") if isinstance(fragment, bytes) else fragment
        for fragment, charset in parts
    )


class ZeptoMailProvider:
    """Sends via the ZeptoMail HTTP API (EU host)."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.email_api_key.get_secret_value()
        self._from = settings.email_from_address
        self._from_name = settings.email_from_name

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        if not self._api_key:
            # Misconfiguration is permanent — retrying cannot supply a key.
            raise PermanentEmailError("ZeptoMail API key is not configured")

        payload: dict = {
            "from": {"address": self._from, "name": self._from_name},
            "to": [{"email_address": {"address": to}}],
            "subject": subject,
            "textbody": body,
            # Transactional mail: no open/click tracking (Decision 13).
            "track_clicks": False,
            "track_opens": False,
        }
        if reply_to:
            payload["reply_to"] = [{"address": reply_to}]

        headers = {
            "Authorization": f"Zoho-enczapikey {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = httpx.post(
                _ZEPTOMAIL_API_URL,
                json=payload,
                headers=headers,
                timeout=_TIMEOUT_SECONDS,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            # Network/timeout — retryable.
            raise TransientEmailError(f"ZeptoMail request failed: {exc}") from exc

        if response.status_code >= 500:
            raise TransientEmailError(
                f"ZeptoMail server error {response.status_code}: {response.text[:500]}"
            )
        if response.status_code == 429:
            # Rate limited — back off and retry.
            raise TransientEmailError("ZeptoMail rate limited (429)")
        if response.status_code >= 400:
            # 4xx — permanent. Distinguish quota/credit exhaustion for alerting.
            text = response.text[:500]
            quota = "credit" in text.lower() or "quota" in text.lower()
            raise PermanentEmailError(
                f"ZeptoMail rejected send ({response.status_code}): {text}",
                quota_exhausted=quota,
            )

        # Success — pull the provider message id if present.
        try:
            data = response.json()
            message_id = data.get("data", [{}])[0].get("message_id")
        except (ValueError, IndexError, AttributeError, KeyError):
            message_id = None
        return message_id
