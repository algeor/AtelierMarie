"""Redaction helpers for Econt settings, logs, and stored event snapshots."""

from collections.abc import Mapping, Sequence
from typing import Any

_REDACTED = "<redacted>"
_SECRET_KEY_PARTS = (
    "authorization",
    "private_key",
    "privatekey",
    "connection_code",
    "token",
    "secret",
    "password",
)


def redact_secret(value: str | None) -> str | None:
    """Return a stable masked marker for configured secrets."""
    if not value:
        return None
    return _REDACTED


def is_secret_key(key: str) -> bool:
    """Whether a mapping key should be redacted as secret-bearing."""
    folded = key.replace("-", "_").casefold()
    return any(part in folded for part in _SECRET_KEY_PARTS)


def redact_mapping(value: Any) -> Any:
    """Recursively redact secret-looking keys from JSON-like data.

    The shape is preserved so stored courier events remain useful for debugging,
    but raw credentials cannot leak into logs, API responses, or snapshots.
    """
    if isinstance(value, Mapping):
        return {
            key: _REDACTED if is_secret_key(str(key)) else redact_mapping(item)
            for key, item in value.items()
        }
    if isinstance(value, str | bytes):
        return value
    if isinstance(value, Sequence):
        return [redact_mapping(item) for item in value]
    return value
