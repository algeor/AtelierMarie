"""Shared slug generation for managed taxonomy terms.

Slugs are stable keys derived from a display name. They are lowercase,
hyphenated, ASCII-only, and unique within a taxonomy table. Collisions get
deterministic numeric suffixes (`-2`, `-3`, ...).
"""

import re

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Convert a display name into a lowercase hyphenated ASCII slug.

    Strips accents to their ASCII base where possible, lowercases, replaces
    every run of non-alphanumeric characters with a single hyphen, and trims
    leading/trailing hyphens. Returns "item" if nothing usable remains.
    """
    import unicodedata

    # Decompose accents (é -> e) and drop non-ASCII bytes.
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")

    slug = _NON_SLUG_CHARS.sub("-", ascii_only.lower()).strip("-")
    return slug or "item"


def unique_slug(base: str, existing: set[str]) -> str:
    """Return `base` if unused, else the first `base-N` (N>=2) not in `existing`.

    Does not mutate `existing`; callers add the returned slug themselves.
    """
    if base not in existing:
        return base
    suffix = 2
    while f"{base}-{suffix}" in existing:
        suffix += 1
    return f"{base}-{suffix}"
