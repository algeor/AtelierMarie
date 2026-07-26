"""Managed site announcement banner: admin read/update + public active read.

Singleton row (`id = 'default'`). The `version` column bumps whenever visible
content or schedule changes, so the public dismiss key changes and a user who
dismissed old copy sees the new banner (see site-banner spec).
"""

import sqlite3

import structlog

from app.database import get_db
from app.services import pricing
from app.utils.sanitize import is_safe_http_or_relative_url

logger = structlog.get_logger(__name__)

_BANNER_ID = "default"

# Fields whose change should bump the version (invalidate prior dismissals).
_VERSIONED_FIELDS = (
    "message_en",
    "message_bg",
    "link_label_en",
    "link_label_bg",
    "link_url",
    "is_enabled",
    "starts_at",
    "ends_at",
)


def _row_to_admin(row: sqlite3.Row) -> dict:
    return {
        "message_en": row["message_en"],
        "message_bg": row["message_bg"],
        "link_label_en": row["link_label_en"],
        "link_label_bg": row["link_label_bg"],
        "link_url": row["link_url"],
        "is_enabled": bool(row["is_enabled"]),
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "version": row["version"],
        "updated_at": row["updated_at"],
    }


def _get_row(conn: sqlite3.Connection) -> sqlite3.Row:
    """Read the singleton banner, seeding a disabled placeholder if absent.

    Used by the admin (read/write) paths only. The public read path must NOT
    seed — see `get_public_banner`.
    """
    row = conn.execute("SELECT * FROM site_banners WHERE id = ?", (_BANNER_ID,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT OR IGNORE INTO site_banners (id, is_enabled, version, updated_at) "
            "VALUES (?, 0, 1, ?)",
            (_BANNER_ID, pricing.now_utc()),
        )
        row = conn.execute("SELECT * FROM site_banners WHERE id = ?", (_BANNER_ID,)).fetchone()
    return row


def get_banner_admin() -> dict:
    """Return the full managed banner settings for the admin editor."""
    with get_db() as conn:
        row = _get_row(conn)
    return _row_to_admin(row)


def update_banner(data: dict) -> dict:
    """Update the managed banner. Bumps version when visible content changes.

    The version increment is expressed as `version + 1` in SQL so a concurrent
    save cannot lose an increment (which would otherwise fail to invalidate
    dismissals of stale copy).
    """
    now = pricing.now_utc()
    with get_db() as conn:
        row = _get_row(conn)

        new_values = {
            "message_en": data.get("message_en"),
            "message_bg": data.get("message_bg"),
            "link_label_en": data.get("link_label_en"),
            "link_label_bg": data.get("link_label_bg"),
            "link_url": data.get("link_url"),
            "is_enabled": 1 if data.get("is_enabled") else 0,
            "starts_at": data.get("starts_at"),
            "ends_at": data.get("ends_at"),
        }

        content_changed = any(
            _normalize(new_values[f]) != _normalize(row[f]) for f in _VERSIONED_FIELDS
        )
        version_sql = "version + 1" if content_changed else "version"

        conn.execute(
            "UPDATE site_banners SET message_en = ?, message_bg = ?, link_label_en = ?, "
            "link_label_bg = ?, link_url = ?, is_enabled = ?, starts_at = ?, ends_at = ?, "
            f"version = {version_sql}, updated_at = ? WHERE id = ?",  # noqa: S608 - literal only
            (
                new_values["message_en"],
                new_values["message_bg"],
                new_values["link_label_en"],
                new_values["link_label_bg"],
                new_values["link_url"],
                new_values["is_enabled"],
                new_values["starts_at"],
                new_values["ends_at"],
                now,
                _BANNER_ID,
            ),
        )
        row = _get_row(conn)

    logger.info("banner_updated", version=row["version"], is_enabled=bool(row["is_enabled"]))
    return _row_to_admin(row)


def _normalize(value: object) -> str:
    """Normalize a value for change comparison (bool→flag, None→'', strings stripped)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value).strip()


def get_public_banner(locale: str = "en") -> dict | None:
    """Return the active localized banner, or None when no banner is visible.

    Visible iff enabled and the current server time is within the (inclusive)
    active window. Never exposes future/expired/disabled banner content. This
    public read never writes: a missing singleton is treated as "no banner".
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM site_banners WHERE id = ?", (_BANNER_ID,)).fetchone()

    if row is None or not row["is_enabled"]:
        return None

    now = pricing.now_utc()
    if row["starts_at"] is not None and now < row["starts_at"]:
        return None
    if row["ends_at"] is not None and now > row["ends_at"]:
        return None

    message = _localized(row, "message", locale)
    if not message:
        return None

    link_label = _localized(row, "link_label", locale)
    link_url = row["link_url"]
    return {
        "message": message,
        "link_label": link_label,
        "link_url": link_url if link_url and is_safe_http_or_relative_url(link_url) else None,
        "dismiss_key": f"{_BANNER_ID}:v{row['version']}",
    }


def _localized(row: sqlite3.Row, prefix: str, locale: str) -> str | None:
    """Return the locale field with fallback from BG to EN."""
    if locale == "bg":
        value = row[f"{prefix}_bg"]
        if value:
            return value
    return row[f"{prefix}_en"]
