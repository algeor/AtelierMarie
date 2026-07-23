"""Email provider abstraction.

`EmailProvider` is a structural Protocol (not an ABC) — any object with a
matching `send()` satisfies it. Two implementations ship: `ConsoleProvider`
(dev/test, no network) and `ZeptoMailProvider` (production HTTP API).

Providers raise a `TransientEmailError` for retryable failures (5xx, timeout,
network) and a `PermanentEmailError` for non-retryable ones (4xx, bad config).
The sweeper uses that distinction to decide backoff vs. `failed_permanent`.
"""

from typing import Protocol, runtime_checkable

from app.config import Settings


class EmailSendError(Exception):
    """Base class for provider send failures."""


class TransientEmailError(EmailSendError):
    """Retryable failure (provider 5xx, timeout, connection error)."""


class PermanentEmailError(EmailSendError):
    """Non-retryable failure (provider 4xx, auth/config error, quota exhausted).

    `quota_exhausted` distinguishes credit/quota errors: retrying cannot fix
    them, so they go terminal + admin alert (a human must top up).
    """

    def __init__(self, message: str, *, quota_exhausted: bool = False) -> None:
        super().__init__(message)
        self.quota_exhausted = quota_exhausted


@runtime_checkable
class EmailProvider(Protocol):
    """Sends one email. Implementations must not add List-Unsubscribe headers
    and must disable open/click tracking (transactional mail — Decision 13)."""

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        """Send a plain-text email. Returns a provider message id if available.

        Raises TransientEmailError / PermanentEmailError on failure.
        """
        ...


def get_email_provider(settings: Settings) -> EmailProvider:
    """Return the configured provider. Factory keyed on `settings.email_provider`.

    Console provider never imports the ZeptoMail sender lib and vice versa.
    """
    if settings.email_provider == "zeptomail":
        from app.email.providers.zeptomail_provider import ZeptoMailProvider

        return ZeptoMailProvider(settings)

    from app.email.providers.console_provider import ConsoleProvider

    return ConsoleProvider(settings)
