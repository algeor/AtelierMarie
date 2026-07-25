"""Pricing helper — the single source of truth for discount math.

Every price consumer (public API, cart totals, checkout snapshot, price sort)
computes discount active-state and effective price through this module. No
consumer implements discount math, active-state, or public display-percent
logic inline — this keeps display and charge from ever diverging.

Timestamps are stored as canonical UTC text `YYYY-MM-DD HH:MM:SS`, matching the
existing `created_at`/`updated_at` convention. Zero-padded strings in this
format compare lexicographically in chronological order, so active-window
checks use direct string comparison after normalization.
"""

from datetime import UTC, datetime

# SQLite-compatible canonical UTC datetime format.
CANONICAL_DT_FMT = "%Y-%m-%d %H:%M:%S"


def now_utc() -> str:
    """Return the current UTC time as canonical `YYYY-MM-DD HH:MM:SS` text."""
    return datetime.now(UTC).strftime(CANONICAL_DT_FMT)


def normalize_discount_datetime(value: str | None) -> str | None:
    """Normalize a discount datetime input to canonical UTC text.

    Accepts:
      - `None`/empty → `None`
      - the canonical stored format `YYYY-MM-DD HH:MM:SS` (interpreted as UTC)
      - any timezone-aware ISO-8601 datetime (converted to UTC)

    Rejects timezone-less input that is not the canonical stored format, so an
    ambiguous wall-clock time can never be silently persisted as UTC.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "discount datetime must be a string"
        raise ValueError(msg)

    text = value.strip()
    if not text:
        return None

    # Canonical stored format — already UTC by convention.
    try:
        parsed = datetime.strptime(text, CANONICAL_DT_FMT).replace(tzinfo=UTC)
        return parsed.strftime(CANONICAL_DT_FMT)
    except ValueError:
        pass

    # ISO-8601: accept a trailing 'Z', require an explicit offset otherwise.
    iso_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(iso_text)
    except ValueError as e:
        msg = f"invalid discount datetime: {value!r}"
        raise ValueError(msg) from e

    if parsed.tzinfo is None:
        msg = (
            "discount datetime must be timezone-aware ISO-8601 "
            f"or canonical UTC 'YYYY-MM-DD HH:MM:SS': {value!r}"
        )
        raise ValueError(msg)

    return parsed.astimezone(UTC).strftime(CANONICAL_DT_FMT)


def discount_is_active(
    percent: int | None,
    starts_at: str | None,
    ends_at: str | None,
    now: str,
) -> bool:
    """Return whether a discount is active at `now` (canonical UTC text).

    Active iff a percent is set AND now is within the (inclusive) window.
    A percent with no dates is active indefinitely (manual on/off).
    """
    if percent is None:
        return False
    if starts_at is not None and now < starts_at:
        return False
    return not (ends_at is not None and now > ends_at)


def effective_price_cents(price_cents: int, percent: int | None, active: bool) -> int:
    """Compute the effective price in cents.

    When active, applies a round-half-up percentage discount using integer
    arithmetic (no float drift) and clamps to a minimum of 1 cent so
    `order_items CHECK (price_cents > 0)` can never be violated. When inactive,
    returns `price_cents` unchanged.
    """
    if not active or percent is None:
        return price_cents
    discounted = (price_cents * (100 - percent) + 50) // 100
    return max(1, discounted)


def annotate_product_pricing(product: dict, now: str, *, public: bool) -> dict:
    """Return a copy of `product` with computed pricing fields added.

    Both variants add `discount_active` and `effective_price_cents`.

    Public variant: `discount_percent` is the active display percent or `None`
    (never leaks a future/expired schedule), and discount window timestamps are
    removed so they are never exposed to shoppers.

    Admin variant: keeps the raw `discount_percent`, `discount_starts_at`, and
    `discount_ends_at` and adds the computed preview values.
    """
    result = dict(product)

    percent = product.get("discount_percent")
    starts_at = product.get("discount_starts_at")
    ends_at = product.get("discount_ends_at")
    price = product["price_cents"]

    active = discount_is_active(percent, starts_at, ends_at, now)
    result["discount_active"] = active
    result["effective_price_cents"] = effective_price_cents(price, percent, active)

    if public:
        # Only expose the percent while active; never expose the window.
        result["discount_percent"] = percent if active else None
        result.pop("discount_starts_at", None)
        result.pop("discount_ends_at", None)

    return result
