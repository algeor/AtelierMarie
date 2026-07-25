"""Log-redaction helpers for email PII (design Decision 23).

There is no structlog redaction processor in this project, so redaction is
applied at the call site. `redact_recipient` yields a stable, non-reversible
token so log lines can be correlated without exposing the raw address.
"""

import hashlib


def redact_recipient(email: str) -> str:
    """Return a truncated, hashed form of an email address for logs.

    Example: ``a***@example.com [sha256:1a2b3c4d]``. Keeps the domain and the
    first local-part character for debuggability, hashes the rest so the full
    address never lands in a log store.
    """
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:8]
    local, _, domain = email.partition("@")
    masked_local = (local[0] + "***") if local else "***"
    if domain:
        return f"{masked_local}@{domain} [sha256:{digest}]"
    return f"{masked_local} [sha256:{digest}]"
