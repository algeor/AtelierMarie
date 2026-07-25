"""Cross-module constants — single source of truth.

Rule: if a value appears in 2+ files, it lives here.
Module-specific constants stay local to their file.
"""

from typing import Literal

# SQLite-compatible datetime format (no T separator, no timezone suffix)
SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Session expiry (in days, used to derive seconds in config)
SESSION_MAX_AGE_DAYS = 30
SESSION_ABSOLUTE_LIFETIME_DAYS = 180
SESSION_SLIDING_THRESHOLD_DAYS = 7

# Pagination bounds
MAX_PAGE = 1000
MAX_LIMIT = 100

# Product value bounds (for validation in CSV import and admin endpoints)
MAX_PRICE_CENTS = 99_999_99  # $99,999.99
# Note: Spec (input-validation) allows up to 1,000,000. We keep the stricter
# cap since real inventories for luxury candles never approach 1M units.
MAX_STOCK = 999_999

# ---------------------------------------------------------------------------
# Payment (payment-integration)
# ---------------------------------------------------------------------------

PaymentMethod = Literal["cod", "card", "bank_transfer"]
PaymentStatus = Literal["pending", "paid", "cod_pending", "failed", "refunded"]

# ---------------------------------------------------------------------------
# Email notifications (design Decision 19 — single canonical event vocabulary)
# ---------------------------------------------------------------------------

# The "event" token is the spine of the email feature: it names the
# order_emails.event column, the template filename (order_{event}.txt), and
# the route logic. It must have exactly one canonical form.
#
# Extension point: 'payment_pending' is NOT an order status — it's a
# payment-lifecycle event queued at order creation for card/bank_transfer
# orders instead of 'placed'. The sweeper treats it identically to other events.
EmailEvent = Literal["placed", "shipped", "delivered", "cancelled", "admin_new_order", "payment_pending"]

# OrderStatus → EmailEvent. None means "no customer email for this transition".
# NOTE: status "pending" maps to event "placed" for COD orders; card/bank_transfer
# orders queue "payment_pending" instead — handled in order_service.checkout().
# "confirmed" sends no email (Decision 9 — pending→confirmed is an internal admin step).
STATUS_TO_EMAIL_EVENT: dict[str, str | None] = {
    "pending": "placed",
    "confirmed": None,
    "shipped": "shipped",
    "delivered": "delivered",
    "cancelled": "cancelled",
}

# ---------------------------------------------------------------------------
# Shipping carriers + tracking URL patterns (design Decision 6 / task 1.6, 2.2)
# ---------------------------------------------------------------------------

# Carrier code → tracking URL pattern. "{num}" is replaced with the tracking
# number. Carriers absent from this map (e.g. "other") get no auto-generated
# URL — the admin must paste one. Used by the order service (auto-generation),
# request validation, and the frontend carrier dropdown.
CARRIER_TRACKING_URL_PATTERNS: dict[str, str] = {
    "speedy": "https://www.speedy.bg/en/track-shipment?shipmentNumber={num}",
    "econt": "https://www.econt.com/services/track-shipment/{num}",
    "dhl": "https://www.dhl.com/en/express/tracking.html?AWB={num}",
    "fedex": "https://www.fedex.com/fedextrack/?trknbr={num}",
}


def tracking_url_for(carrier: str | None, number: str | None) -> str | None:
    """Return the auto-generated tracking URL for a known carrier, else None."""
    if not carrier or not number:
        return None
    pattern = CARRIER_TRACKING_URL_PATTERNS.get(carrier.lower())
    if pattern is None:
        return None
    return pattern.format(num=number)
