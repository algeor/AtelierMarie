"""Shared slug generation for managed taxonomy terms.

Slugs are stable keys derived from a display name. They are lowercase,
hyphenated, ASCII-only, and unique within a taxonomy table. Collisions get
deterministic numeric suffixes (`-2`, `-3`, ...).

Cyrillic input (Bulgarian names) is transliterated to Latin before ASCII
stripping so terms keep meaningful, readable slugs (`Зима` -> `zima`) instead
of collapsing to the `"item"` fallback.
"""

import re
import unicodedata

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")

# Bulgarian Cyrillic -> Latin transliteration (official streamlined system).
# Applied before ASCII stripping so Cyrillic display names produce readable
# slugs rather than degrading to "item". Order matters for multi-char outputs.
_CYRILLIC_TRANSLITERATION = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sht",
    "ъ": "a",
    "ь": "y",
    "ю": "yu",
    "я": "ya",
}


def _transliterate(value: str) -> str:
    """Map Cyrillic characters to Latin; leave everything else untouched."""
    return "".join(_CYRILLIC_TRANSLITERATION.get(ch, ch) for ch in value.lower())


def slugify(value: str) -> str:
    """Convert a display name into a lowercase hyphenated ASCII slug.

    Transliterates Cyrillic to Latin, strips accents to their ASCII base where
    possible, lowercases, replaces every run of non-alphanumeric characters with
    a single hyphen, and trims leading/trailing hyphens. Returns "item" if
    nothing usable remains.
    """
    transliterated = _transliterate(value)
    # Decompose accents (é -> e) and drop any remaining non-ASCII bytes.
    normalized = unicodedata.normalize("NFKD", transliterated)
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
