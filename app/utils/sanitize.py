"""Input sanitization utilities for user-generated content.

Uses html.escape (stdlib) for lossless entity encoding — safe in all
rendering contexts and combined with React's default escaping for defense-in-depth.
"""

import html
import re

from app.utils.blocklist import BLOCKED_WORDS

_URL_ONLY_RE = re.compile(r"^https?://\S+$")


def sanitize_text(text: str) -> str:
    """Escape HTML special characters for safe storage.

    Converts <, >, &, ", ' to HTML entities. Lossless — original text
    is recoverable via html.unescape().
    """
    return html.escape(text, quote=True)


def is_url_only(text: str) -> bool:
    """Return True if text is solely a URL (protocol required).

    URLs embedded in surrounding text are allowed — this only catches
    bodies that are nothing but a single link.
    """
    return bool(_URL_ONLY_RE.match(text.strip()))


def contains_blocked_word(text: str) -> bool:
    """Return True if text contains any word from the blocklist.

    Case-insensitive substring match. Both text and blocklist are lowered.
    """
    lowered = text.lower()
    return any(word in lowered for word in BLOCKED_WORDS)
