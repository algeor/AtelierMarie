"""Admin-managed reusable site media slots."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg
import structlog

from app.config import get_settings
from app.database import get_db
from app.services.image_service import process_image, validate_image_file

logger = structlog.get_logger(__name__)
_DT_FMT = "%Y-%m-%d %H:%M:%S"


class SiteMediaNotFoundError(Exception):
    """Raised when an unknown media slot key is requested."""


@dataclass(frozen=True)
class SiteMediaSlot:
    key: str
    owner_slug: str
    label: str
    description: str
    default_url: str | None
    sort_order: int


SLOTS: tuple[SiteMediaSlot, ...] = (
    SiteMediaSlot(
        key="home_hero",
        owner_slug="site-media-home-hero",
        label="Homepage hero image",
        description=(
            "Optional direct hero photo. When empty, the homepage keeps using the "
            "featured product image."
        ),
        default_url=None,
        sort_order=10,
    ),
    SiteMediaSlot(
        key="home_hero_fallback",
        owner_slug="site-media-home-hero-fallback",
        label="Homepage hero fallback",
        description="Used only when there is no direct hero image and no usable product image.",
        default_url="/rebrand/error-candle.webp",
        sort_order=20,
    ),
    SiteMediaSlot(
        key="atelier_hero_fallback",
        owner_slug="site-media-atelier-hero",
        label="Atelier hero fallback",
        description=(
            "Fallback image for the Atelier hero section when that section has no uploaded image."
        ),
        default_url="/rebrand/error-candle.webp",
        sort_order=30,
    ),
    SiteMediaSlot(
        key="atelier_story_fallback",
        owner_slug="site-media-atelier-story",
        label="Atelier story fallback",
        description=(
            "Fallback image for the Atelier story section when that section has no uploaded image."
        ),
        default_url="/rebrand/error-candle.webp",
        sort_order=40,
    ),
    SiteMediaSlot(
        key="atelier_atelier_fallback",
        owner_slug="site-media-atelier-inside",
        label="Inside atelier fallback",
        description=(
            "Fallback image for the Inside Atelier section when that section has no uploaded image."
        ),
        default_url="/rebrand/error-candle.webp",
        sort_order=50,
    ),
    SiteMediaSlot(
        key="atelier_collections_fallback",
        owner_slug="site-media-atelier-collections",
        label="Atelier collections fallback",
        description="Fallback image for collection cards when an item has no uploaded image.",
        default_url="/rebrand/error-candle.webp",
        sort_order=60,
    ),
    SiteMediaSlot(
        key="atelier_process_fallback",
        owner_slug="site-media-atelier-process",
        label="Atelier process fallback",
        description=(
            "Fallback image for the Atelier process section when that section has no "
            "uploaded image."
        ),
        default_url="/rebrand/error-candle.webp",
        sort_order=70,
    ),
    SiteMediaSlot(
        key="error_page_image",
        owner_slug="site-media-error-page",
        label="Error page image",
        description="Image shown on branded 404 and error recovery pages.",
        default_url="/rebrand/error-candle.webp",
        sort_order=80,
    ),
    SiteMediaSlot(
        key="page_background",
        owner_slug="site-media-page-background",
        label="Page background texture",
        description="Subtle background image layered behind storefront pages.",
        default_url="/rebrand/watercolor-page-bg.webp",
        sort_order=90,
    ),
)

_SLOT_BY_KEY = {slot.key: slot for slot in SLOTS}


def _slot_for(key: str) -> SiteMediaSlot:
    try:
        return _SLOT_BY_KEY[key]
    except KeyError as exc:
        raise SiteMediaNotFoundError(key) from exc


def _ensure_rows(conn: psycopg.Connection) -> None:
    for slot in SLOTS:
        conn.execute(
            "INSERT INTO site_media_assets (key) VALUES (%s) ON CONFLICT (key) DO NOTHING",
            (slot.key,),
        )


def _format_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


def _row_to_admin(row: dict, slot: SiteMediaSlot) -> dict:
    return {
        "key": slot.key,
        "label": slot.label,
        "description": slot.description,
        "default_url": slot.default_url,
        "image_id": row["image_id"],
        "image_url": row["image_url"],
        "thumbnail_url": row["thumbnail_url"],
        "zoom_url": row["zoom_url"],
        "effective_url": row["image_url"] or slot.default_url,
        "updated_at": _format_timestamp(row["updated_at"]),
    }


def list_admin_assets() -> dict:
    """Return all media slots with admin labels and current upload state."""
    with get_db() as conn:
        _ensure_rows(conn)
        rows = {
            row["key"]: row for row in conn.execute("SELECT * FROM site_media_assets").fetchall()
        }
    return {"assets": [_row_to_admin(rows[slot.key], slot) for slot in SLOTS]}


def get_public_assets() -> dict:
    """Return effective public URLs by slot key."""
    with get_db() as conn:
        _ensure_rows(conn)
        rows = {
            row["key"]: row for row in conn.execute("SELECT * FROM site_media_assets").fetchall()
        }
    return {"assets": {slot.key: rows[slot.key]["image_url"] or slot.default_url for slot in SLOTS}}


def set_asset_image(key: str, file_bytes: bytes) -> dict:
    """Upload and replace the image for one media slot."""
    slot = _slot_for(key)
    validate_image_file(file_bytes, slot.owner_slug)
    image_id = uuid.uuid4().hex
    processed = process_image(file_bytes, slot.owner_slug, image_id=image_id)

    with get_db() as conn:
        _ensure_rows(conn)
        old = conn.execute("SELECT * FROM site_media_assets WHERE key = %s", (key,)).fetchone()
        conn.execute(
            """
            UPDATE site_media_assets
            SET image_id = %s, image_url = %s, thumbnail_url = %s, zoom_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE key = %s
            """,
            (
                image_id,
                processed["image_url"],
                processed["thumbnail_url"],
                processed["zoom_url"],
                key,
            ),
        )
        row = conn.execute("SELECT * FROM site_media_assets WHERE key = %s", (key,)).fetchone()

    if old:
        _unlink_image_files(old["image_url"], old["thumbnail_url"], old["zoom_url"])
    logger.info("site_media_uploaded", key=key)
    return _row_to_admin(row, slot)


def clear_asset_image(key: str) -> dict:
    """Clear one uploaded image and fall back to the bundled default."""
    slot = _slot_for(key)
    with get_db() as conn:
        _ensure_rows(conn)
        old = conn.execute("SELECT * FROM site_media_assets WHERE key = %s", (key,)).fetchone()
        conn.execute(
            """
            UPDATE site_media_assets
            SET image_id = NULL, image_url = NULL, thumbnail_url = NULL, zoom_url = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE key = %s
            """,
            (key,),
        )
        row = conn.execute("SELECT * FROM site_media_assets WHERE key = %s", (key,)).fetchone()

    if old:
        _unlink_image_files(old["image_url"], old["thumbnail_url"], old["zoom_url"])
    logger.info("site_media_cleared", key=key)
    return _row_to_admin(row, slot)


def _unlink_image_files(*urls: str | None) -> None:
    static_root = Path(get_settings().static_file_path).resolve()
    for url in urls:
        if not url or not url.startswith("/static/"):
            continue
        relative = url.removeprefix("/static/")
        path = (static_root / relative).resolve()
        try:
            path.relative_to(static_root)
        except ValueError:
            logger.warning("site_media_unlink_rejected", path=str(path))
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("site_media_unlink_failed", path=str(path), error=str(exc))
