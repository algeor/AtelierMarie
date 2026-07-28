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

# CSV bulk-import limits — bound memory and DB round-trips per upload.
MAX_CSV_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_CSV_ROWS = 10_000

# ---------------------------------------------------------------------------
# Email notifications (design Decision 19 — single canonical event vocabulary)
# ---------------------------------------------------------------------------

# The "event" token is the spine of the email feature: it names the
# order_emails.event column, the template filename (order_{event}.txt), and
# the route logic. It must have exactly one canonical form.
EmailEvent = Literal["placed", "shipped", "delivered", "cancelled", "admin_new_order"]

# OrderStatus → EmailEvent. None means "no customer email for this transition".
# NOTE: status "pending" maps to event "placed"; "confirmed" sends no email
# (Decision 9 — pending→confirmed is an internal admin step).
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

# ---------------------------------------------------------------------------
# Product video transcoding
# ---------------------------------------------------------------------------

VIDEO_TRANSCODE_CRF = "20"
VIDEO_TRANSCODE_PRESET = "slow"
VIDEO_TRANSCODE_MAX_HEIGHT = 1080
VIDEO_AUDIO_BITRATE = "128k"
VIDEO_POSTER_TIMESTAMP_SECONDS = "1"
VIDEO_SWEEPER_INTERVAL_SECONDS = 15
VIDEO_TRANSCODE_LEASE_SECONDS = 20 * 60
VIDEO_FFMPEG_NICE_LEVEL = "10"
VIDEO_FFMPEG_IONICE_CLASS = "2"
VIDEO_FFMPEG_IONICE_LEVEL = "7"

VIDEO_TRANSCODE_ARGS = (
    "-map",
    "0:v:0",
    "-map",
    "0:a?",
    "-c:v",
    "libx264",
    "-profile:v",
    "high",
    "-pix_fmt",
    "yuv420p",
    "-crf",
    VIDEO_TRANSCODE_CRF,
    "-preset",
    VIDEO_TRANSCODE_PRESET,
    "-vf",
    f"scale='min(iw,-2)':min({VIDEO_TRANSCODE_MAX_HEIGHT},ih):force_original_aspect_ratio=decrease",
    "-c:a",
    "aac",
    "-b:a",
    VIDEO_AUDIO_BITRATE,
    "-movflags",
    "+faststart",
)


def tracking_url_for(carrier: str | None, number: str | None) -> str | None:
    """Return the auto-generated tracking URL for a known carrier, else None."""
    if not carrier or not number:
        return None
    pattern = CARRIER_TRACKING_URL_PATTERNS.get(carrier.lower())
    if pattern is None:
        return None
    return pattern.format(num=number)
