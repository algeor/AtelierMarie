"""Service layer for the editable atelier story page."""

import uuid

from app.database import DbConnection, get_db, require_row
from app.services import object_storage_service
from app.services.image_service import process_image, validate_image_file
from app.utils.sanitize import is_safe_http_or_relative_url, sanitize_text, unsanitize_text

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_ts(value: object) -> str | None:
    """Render a timestamp column (datetime or str) as the canonical string."""
    from datetime import datetime

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


class AboutSectionNotFoundError(Exception):
    """Raised when an about section slug does not exist."""


class AboutItemNotFoundError(Exception):
    """Raised when an about item id does not exist under the requested section."""


class AboutReorderError(Exception):
    """Raised when a reorder request does not match the current row set."""


class AboutValidationError(Exception):
    """Raised for invalid editable about content."""


_SECTION_TEXT_FIELDS = {
    "heading_en",
    "heading_bg",
    "subheading_en",
    "subheading_bg",
    "body_en",
    "body_bg",
    "cta_label_en",
    "cta_label_bg",
}
_SECTION_URL_FIELDS = {"cta_href"}
_ITEM_TEXT_FIELDS = {"title_en", "title_bg", "text_en", "text_bg"}
_ITEM_URL_FIELDS = {"link_href"}


def _image_url(owner_slug: str, image_id: str | None) -> str | None:
    if not image_id:
        return None
    # Owner images are uploaded to R2 under the shared products/ prefix with the
    # same stem as product images. Reconstruct the R2 public URL from the stored
    # image_id. If R2 is unconfigured (dev/test without R2), degrade gracefully
    # to no image rather than crashing a read path.
    key = object_storage_service.object_key_for_stem(f"{owner_slug}_{image_id}", ".webp")
    try:
        return object_storage_service.public_url(key)
    except object_storage_service.StorageConfigError:
        return f"/static/products/{key.rsplit('/', 1)[-1]}"


def _section_owner_slug(slug: str) -> str:
    return f"about-{slug.replace('_', '-')}"


def _item_owner_slug(item_id: int) -> str:
    return f"about-item-{item_id}"


def _sanitize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return sanitize_text(stripped)


def _sanitize_required(value: str) -> str:
    sanitized = _sanitize_optional(value)
    if sanitized is None:
        raise AboutValidationError("Required text cannot be blank")
    return sanitized


def _clean_url(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if not is_safe_http_or_relative_url(stripped):
        raise AboutValidationError("URL must be http(s) or a safe relative URL")
    return stripped


def _public_section_dict(row: dict) -> dict:
    cta = None
    if row["cta_label"] and row["cta_href"]:
        cta = {"label": unsanitize_text(row["cta_label"]), "href": row["cta_href"]}
    return {
        "slug": row["slug"],
        "type": row["type"],
        "heading": unsanitize_text(row["heading"]),
        "subheading": unsanitize_text(row["subheading"]),
        "body": unsanitize_text(row["body"]),
        "cta": cta,
        "image": _image_url(_section_owner_slug(row["slug"]), row["image_id"]),
        "items": [],
    }


def _admin_item_dict(row: dict) -> dict:
    item_id = int(row["id"])
    return {
        "id": item_id,
        "section": row["section"],
        "title_en": unsanitize_text(row["title_en"]),
        "title_bg": unsanitize_text(row["title_bg"]),
        "text_en": unsanitize_text(row["text_en"]),
        "text_bg": unsanitize_text(row["text_bg"]),
        "image_id": row["image_id"],
        "image": _image_url(_item_owner_slug(item_id), row["image_id"]),
        "link_href": row["link_href"],
        "sort_order": row["sort_order"],
        "is_published": bool(row["is_published"]),
        "created_at": _fmt_ts(row["created_at"]),
        "updated_at": _fmt_ts(row["updated_at"]),
    }


def _admin_section_dict(row: dict) -> dict:
    return {
        "slug": row["slug"],
        "type": row["type"],
        "heading_en": unsanitize_text(row["heading_en"]),
        "heading_bg": unsanitize_text(row["heading_bg"]),
        "subheading_en": unsanitize_text(row["subheading_en"]),
        "subheading_bg": unsanitize_text(row["subheading_bg"]),
        "body_en": unsanitize_text(row["body_en"]),
        "body_bg": unsanitize_text(row["body_bg"]),
        "cta_label_en": unsanitize_text(row["cta_label_en"]),
        "cta_label_bg": unsanitize_text(row["cta_label_bg"]),
        "cta_href": row["cta_href"],
        "image_id": row["image_id"],
        "image": _image_url(_section_owner_slug(row["slug"]), row["image_id"]),
        "sort_order": row["sort_order"],
        "is_published": bool(row["is_published"]),
        "created_at": _fmt_ts(row["created_at"]),
        "updated_at": _fmt_ts(row["updated_at"]),
        "items": [],
    }


def get_public_about(locale: str = "en") -> dict:
    """Return published localized about sections and published items."""
    localized = locale == "bg"
    section_select = (
        "COALESCE(heading_bg, heading_en) AS heading, "
        "COALESCE(subheading_bg, subheading_en) AS subheading, "
        "COALESCE(body_bg, body_en) AS body, "
        "COALESCE(cta_label_bg, cta_label_en) AS cta_label"
        if localized
        else "heading_en AS heading, subheading_en AS subheading, body_en AS body, "
        "cta_label_en AS cta_label"
    )
    item_select = (
        "COALESCE(title_bg, title_en) AS title, COALESCE(text_bg, text_en) AS text"
        if localized
        else "title_en AS title, text_en AS text"
    )

    with get_db() as conn:
        section_rows = conn.execute(
            f"""
            SELECT slug, type, {section_select}, cta_href, image_id
            FROM about_sections
            WHERE is_published = 1
            ORDER BY sort_order, slug
            """  # noqa: S608 - select fragment is fixed by locale only.
        ).fetchall()
        sections = [_public_section_dict(row) for row in section_rows]
        by_slug = {section["slug"]: section for section in sections}

        if by_slug:
            placeholders = ", ".join("%s" for _ in by_slug)
            item_rows = conn.execute(
                f"""
                SELECT id, section, {item_select}, image_id, link_href
                FROM about_items
                WHERE is_published = 1 AND section IN ({placeholders})
                ORDER BY section, sort_order, id
                """,  # noqa: S608 - placeholders generated from section count.
                list(by_slug),
            ).fetchall()
            for row in item_rows:
                item_id = int(row["id"])
                by_slug[row["section"]]["items"].append(
                    {
                        "id": item_id,
                        "title": unsanitize_text(row["title"]),
                        "text": unsanitize_text(row["text"]),
                        "image": _image_url(_item_owner_slug(item_id), row["image_id"]),
                        "link": row["link_href"],
                    }
                )
    return {"sections": sections}


def list_admin_about() -> dict:
    """Return all raw bilingual about sections and items for admin editing."""
    with get_db() as conn:
        section_rows = conn.execute(
            "SELECT * FROM about_sections ORDER BY sort_order, slug"
        ).fetchall()
        sections = [_admin_section_dict(row) for row in section_rows]
        by_slug = {section["slug"]: section for section in sections}
        item_rows = conn.execute(
            "SELECT * FROM about_items ORDER BY section, sort_order, id"
        ).fetchall()
        for row in item_rows:
            section = by_slug.get(row["section"])
            if section is not None:
                section["items"].append(_admin_item_dict(row))
    return {"sections": sections}


def _ensure_section_exists(conn: DbConnection, slug: str) -> None:
    row = conn.execute("SELECT 1 FROM about_sections WHERE slug = %s", (slug,)).fetchone()
    if row is None:
        raise AboutSectionNotFoundError(f"About section not found: {slug}")


def _ensure_item_exists(conn: DbConnection, section: str, item_id: int) -> None:
    row = conn.execute(
        "SELECT 1 FROM about_items WHERE section = %s AND id = %s", (section, item_id)
    ).fetchone()
    if row is None:
        raise AboutItemNotFoundError(f"About item not found: {item_id}")


def update_section_text(slug: str, updates: dict) -> dict:
    """Patch editable section text/CTA fields. Slug and type are immutable."""
    fields: dict[str, object] = {}
    for key, value in updates.items():
        if key in _SECTION_TEXT_FIELDS:
            fields[key] = (
                _sanitize_required(value) if key == "heading_en" else _sanitize_optional(value)
            )
        elif key in _SECTION_URL_FIELDS:
            fields[key] = _clean_url(value)
        else:
            raise AboutValidationError(f"Field cannot be edited: {key}")

    with get_db() as conn:
        _ensure_section_exists(conn, slug)
        if fields:
            fields["updated_at"] = "CURRENT_TIMESTAMP"
            set_clause = ", ".join(
                f"{key} = CURRENT_TIMESTAMP" if key == "updated_at" else f"{key} = %s"
                for key in fields
            )
            values = [value for key, value in fields.items() if key != "updated_at"]
            conn.execute(f"UPDATE about_sections SET {set_clause} WHERE slug = %s", [*values, slug])
    return next(s for s in list_admin_about()["sections"] if s["slug"] == slug)


def create_item(section: str, payload: dict) -> dict:
    """Create an about item with the next sort order under a section."""
    fields = {
        "title_en": _sanitize_required(payload["title_en"]),
        "title_bg": _sanitize_optional(payload.get("title_bg")),
        "text_en": _sanitize_optional(payload.get("text_en")),
        "text_bg": _sanitize_optional(payload.get("text_bg")),
        "link_href": _clean_url(payload.get("link_href")),
        "is_published": 1 if payload.get("is_published", True) else 0,
    }
    with get_db() as conn:
        _ensure_section_exists(conn, section)
        row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) AS max_order FROM about_items WHERE section = %s",
            (section,),
        ).fetchone()
        sort_order = int(require_row(row)["max_order"]) + 1
        cursor = conn.execute(
            """
            INSERT INTO about_items (
                section, title_en, title_bg, text_en, text_bg, link_href,
                sort_order, is_published, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                section,
                fields["title_en"],
                fields["title_bg"],
                fields["text_en"],
                fields["text_bg"],
                fields["link_href"],
                sort_order,
                fields["is_published"],
            ),
        )
        inserted = cursor.fetchone()
        item_id = inserted["id"] if inserted else None
        if item_id is None:
            raise RuntimeError("About item insert did not return an id")
    return get_admin_item(section, item_id)


def get_admin_item(section: str, item_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM about_items WHERE section = %s AND id = %s", (section, item_id)
        ).fetchone()
        if row is None:
            raise AboutItemNotFoundError(f"About item not found: {item_id}")
        return _admin_item_dict(row)


def update_item(section: str, item_id: int, updates: dict) -> dict:
    """Patch editable fields on an about item."""
    fields: dict[str, object] = {}
    for key, value in updates.items():
        if key in _ITEM_TEXT_FIELDS:
            fields[key] = (
                _sanitize_required(value) if key == "title_en" else _sanitize_optional(value)
            )
        elif key in _ITEM_URL_FIELDS:
            fields[key] = _clean_url(value)
        elif key == "is_published":
            fields[key] = 1 if value else 0
        else:
            raise AboutValidationError(f"Field cannot be edited: {key}")

    with get_db() as conn:
        _ensure_item_exists(conn, section, item_id)
        if fields:
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE about_items SET {set_clause}, updated_at = CURRENT_TIMESTAMP "
                "WHERE section = %s AND id = %s",
                [*fields.values(), section, item_id],
            )
    return get_admin_item(section, item_id)


def delete_item(section: str, item_id: int) -> None:
    with get_db() as conn:
        _ensure_item_exists(conn, section, item_id)
        conn.execute("DELETE FROM about_items WHERE section = %s AND id = %s", (section, item_id))


def reorder_sections(slugs: list[str]) -> list[dict]:
    """Replace section sort order; submitted set must match current sections."""
    with get_db() as conn:
        rows = conn.execute("SELECT slug FROM about_sections ORDER BY sort_order, slug").fetchall()
        current = [row["slug"] for row in rows]
        if set(current) != set(slugs) or len(current) != len(slugs):
            raise AboutReorderError("slugs must match all about sections")
        for sort_order, slug in enumerate(slugs):
            conn.execute(
                "UPDATE about_sections SET sort_order = %s, updated_at = CURRENT_TIMESTAMP "
                "WHERE slug = %s",
                (sort_order, slug),
            )
    return list_admin_about()["sections"]


def reorder_items(section: str, ids: list[int]) -> list[dict]:
    """Replace item order within a section; submitted set must match current items."""
    with get_db() as conn:
        _ensure_section_exists(conn, section)
        rows = conn.execute(
            "SELECT id FROM about_items WHERE section = %s ORDER BY sort_order, id", (section,)
        ).fetchall()
        current = [int(row["id"]) for row in rows]
        if set(current) != set(ids) or len(current) != len(ids):
            raise AboutReorderError("ids must match all items for the section")
        for sort_order, item_id in enumerate(ids):
            conn.execute(
                "UPDATE about_items SET sort_order = %s, updated_at = CURRENT_TIMESTAMP "
                "WHERE section = %s AND id = %s",
                (sort_order, section, item_id),
            )
    return [
        item for s in list_admin_about()["sections"] if s["slug"] == section for item in s["items"]
    ]


def set_section_published(slug: str, is_published: bool) -> dict:
    with get_db() as conn:
        _ensure_section_exists(conn, slug)
        conn.execute(
            "UPDATE about_sections SET is_published = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE slug = %s",
            (1 if is_published else 0, slug),
        )
    return next(s for s in list_admin_about()["sections"] if s["slug"] == slug)


def set_item_published(section: str, item_id: int, is_published: bool) -> dict:
    with get_db() as conn:
        _ensure_item_exists(conn, section, item_id)
        conn.execute(
            "UPDATE about_items SET is_published = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE section = %s AND id = %s",
            (1 if is_published else 0, section, item_id),
        )
    return get_admin_item(section, item_id)


def set_section_image(slug: str, file_bytes: bytes) -> dict:
    owner_slug = _section_owner_slug(slug)
    validate_image_file(file_bytes, owner_slug)
    image_id = uuid.uuid4().hex
    with get_db() as conn:
        _ensure_section_exists(conn, slug)
        process_image(file_bytes, owner_slug, image_id=image_id)
        conn.execute(
            "UPDATE about_sections SET image_id = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE slug = %s",
            (image_id, slug),
        )
    return next(s for s in list_admin_about()["sections"] if s["slug"] == slug)


def clear_section_image(slug: str) -> dict:
    with get_db() as conn:
        _ensure_section_exists(conn, slug)
        conn.execute(
            "UPDATE about_sections SET image_id = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE slug = %s",
            (slug,),
        )
    return next(s for s in list_admin_about()["sections"] if s["slug"] == slug)


def set_item_image(section: str, item_id: int, file_bytes: bytes) -> dict:
    owner_slug = _item_owner_slug(item_id)
    validate_image_file(file_bytes, owner_slug)
    image_id = uuid.uuid4().hex
    with get_db() as conn:
        _ensure_item_exists(conn, section, item_id)
        process_image(file_bytes, owner_slug, image_id=image_id)
        conn.execute(
            "UPDATE about_items SET image_id = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE section = %s AND id = %s",
            (image_id, section, item_id),
        )
    return get_admin_item(section, item_id)


def clear_item_image(section: str, item_id: int) -> dict:
    with get_db() as conn:
        _ensure_item_exists(conn, section, item_id)
        conn.execute(
            "UPDATE about_items SET image_id = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE section = %s AND id = %s",
            (section, item_id),
        )
    return get_admin_item(section, item_id)
