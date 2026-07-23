"""Console email provider — logs to structlog, never touches the network.

Used for local development and tests: `make dev-backend` and the whole test
suite run with `EMAIL_PROVIDER=console`, so no real mail is ever sent. It never
imports the ZeptoMail sender lib.
"""

import structlog

from app.config import Settings
from app.email.redaction import redact_recipient

logger = structlog.get_logger(__name__)


class ConsoleProvider:
    """Logs the email instead of sending it.

    In non-production it logs the full recipient, subject, and body so a
    developer can read the message. In production (should not normally run the
    console provider, but be safe) it redacts the recipient and omits the body
    per the log-redaction decision (design Decision 23).
    """

    def __init__(self, settings: Settings) -> None:
        self._from = settings.email_from_address
        self._from_name = settings.email_from_name
        self._production = settings.environment == "production"

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        if self._production:
            logger.info(
                "email_console_send",
                to=redact_recipient(to),
                subject=subject,
                reply_to=reply_to,
                tags=tags,
            )
        else:
            logger.info(
                "email_console_send",
                to=to,
                subject=subject,
                reply_to=reply_to,
                tags=tags,
                body=body,
                sender=f"{self._from_name} <{self._from}>",
            )
        # No provider message id for the console transport.
        return None
