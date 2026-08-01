"""Service layer for admin-managed Cookie Policy content."""

import json
import sqlite3

from app.database import get_db
from app.models.cookies import MAX_COOKIE_TEXT_LENGTH


class CookiesNotFoundError(Exception):
    """Raised when the Cookie Policy singleton, inventory row, or section is missing."""


class CookiesValidationError(Exception):
    """Raised for invalid editable Cookie Policy content."""


_PAGE_FIELDS = {
    "meta_title_en",
    "meta_title_bg",
    "meta_description_en",
    "meta_description_bg",
    "eyebrow_en",
    "eyebrow_bg",
    "title_en",
    "title_bg",
    "subtitle_en",
    "subtitle_bg",
    "last_updated_en",
    "last_updated_bg",
    "inventory_title_en",
    "inventory_title_bg",
    "header_name_en",
    "header_name_bg",
    "header_purpose_en",
    "header_purpose_bg",
    "header_type_en",
    "header_type_bg",
    "header_duration_en",
    "header_duration_bg",
}
_REQUIRED_PAGE_FIELDS = {field for field in _PAGE_FIELDS if field.endswith("_en")}

_INVENTORY_FIELDS = {
    "purpose_en",
    "purpose_bg",
    "type_en",
    "type_bg",
    "duration_en",
    "duration_bg",
}
_REQUIRED_INVENTORY_FIELDS = {"purpose_en", "type_en", "duration_en"}

_SECTION_TEXT_FIELDS = {"title_en", "title_bg"}
_SECTION_ARRAY_FIELDS = {"body_en", "body_bg"}
_REQUIRED_SECTION_FIELDS = {"title_en", "body_en"}


def _public_locale(locale: str | None) -> str:
    return "bg" if locale == "bg" else "en"


def _json_lines(value: str | None) -> list[str] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    lines = [str(line) for line in parsed if str(line).strip()]
    return lines or None


def _localized_text(row: sqlite3.Row, field: str, locale: str) -> str:
    en = row[f"{field}_en"]
    bg = row[f"{field}_bg"]
    if locale == "bg" and bg:
        return bg
    return en


def _localized_lines(row: sqlite3.Row, field: str, locale: str) -> list[str]:
    en = _json_lines(row[f"{field}_en"]) or []
    bg = _json_lines(row[f"{field}_bg"])
    if locale == "bg" and bg:
        return bg
    return en


def _page_to_admin_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "meta_title_en": row["meta_title_en"],
        "meta_title_bg": row["meta_title_bg"],
        "meta_description_en": row["meta_description_en"],
        "meta_description_bg": row["meta_description_bg"],
        "eyebrow_en": row["eyebrow_en"],
        "eyebrow_bg": row["eyebrow_bg"],
        "title_en": row["title_en"],
        "title_bg": row["title_bg"],
        "subtitle_en": row["subtitle_en"],
        "subtitle_bg": row["subtitle_bg"],
        "last_updated_en": row["last_updated_en"],
        "last_updated_bg": row["last_updated_bg"],
        "inventory_title_en": row["inventory_title_en"],
        "inventory_title_bg": row["inventory_title_bg"],
        "header_name_en": row["header_name_en"],
        "header_name_bg": row["header_name_bg"],
        "header_purpose_en": row["header_purpose_en"],
        "header_purpose_bg": row["header_purpose_bg"],
        "header_type_en": row["header_type_en"],
        "header_type_bg": row["header_type_bg"],
        "header_duration_en": row["header_duration_en"],
        "header_duration_bg": row["header_duration_bg"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _inventory_to_admin_dict(row: sqlite3.Row) -> dict:
    return {
        "name": row["name"],
        "purpose_en": row["purpose_en"],
        "purpose_bg": row["purpose_bg"],
        "type_en": row["type_en"],
        "type_bg": row["type_bg"],
        "duration_en": row["duration_en"],
        "duration_bg": row["duration_bg"],
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _section_to_admin_dict(row: sqlite3.Row) -> dict:
    return {
        "slug": row["slug"],
        "title_en": row["title_en"],
        "title_bg": row["title_bg"],
        "body_en": _json_lines(row["body_en"]) or [],
        "body_bg": _json_lines(row["body_bg"]),
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_page(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cookies_page WHERE id = 'cookies'").fetchone()
    if row is None:
        raise CookiesNotFoundError("Cookie Policy page not found")
    return row


def _get_inventory_item(conn: sqlite3.Connection, name: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cookies_inventory WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise CookiesNotFoundError(f"Cookie inventory row not found: {name}")
    return row


def _get_section(conn: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cookies_sections WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise CookiesNotFoundError(f"Cookie Policy section not found: {slug}")
    return row


def _clean_text(value: str | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise CookiesValidationError("Required text cannot be null")
        return None
    stripped = value.strip()
    if not stripped:
        if required:
            raise CookiesValidationError("Required text cannot be blank")
        return None
    return stripped


def _clean_lines(value: list[str] | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise CookiesValidationError("Required section body cannot be null")
        return None
    lines = [str(line).strip() for line in value if str(line).strip()]
    if not lines:
        if required:
            raise CookiesValidationError("Required section body cannot be blank")
        return None
    if any(len(line) > MAX_COOKIE_TEXT_LENGTH for line in lines):
        raise CookiesValidationError("A Cookie Policy paragraph is too long")
    return json.dumps(lines, ensure_ascii=False)


def get_public_cookies(locale: str | None = "en") -> dict:
    """Return localized Cookie Policy content for the storefront."""
    resolved = _public_locale(locale)
    with get_db() as conn:
        page = _get_page(conn)
        inventory_rows = conn.execute(
            "SELECT * FROM cookies_inventory ORDER BY sort_order, name"
        ).fetchall()
        section_rows = conn.execute(
            "SELECT * FROM cookies_sections ORDER BY sort_order, slug"
        ).fetchall()

    return {
        "meta_title": _localized_text(page, "meta_title", resolved),
        "meta_description": _localized_text(page, "meta_description", resolved),
        "eyebrow": _localized_text(page, "eyebrow", resolved),
        "title": _localized_text(page, "title", resolved),
        "subtitle": _localized_text(page, "subtitle", resolved),
        "last_updated": _localized_text(page, "last_updated", resolved),
        "inventory_title": _localized_text(page, "inventory_title", resolved),
        "headers": {
            "name": _localized_text(page, "header_name", resolved),
            "purpose": _localized_text(page, "header_purpose", resolved),
            "type": _localized_text(page, "header_type", resolved),
            "duration": _localized_text(page, "header_duration", resolved),
        },
        "cookies": [
            {
                "name": row["name"],
                "purpose": _localized_text(row, "purpose", resolved),
                "type": _localized_text(row, "type", resolved),
                "duration": _localized_text(row, "duration", resolved),
            }
            for row in inventory_rows
        ],
        "sections": [
            {
                "id": row["slug"],
                "title": _localized_text(row, "title", resolved),
                "body": _localized_lines(row, "body", resolved),
            }
            for row in section_rows
        ],
    }


def list_admin_cookies() -> dict:
    """Return raw bilingual Cookie Policy content for admin editing."""
    with get_db() as conn:
        page = _page_to_admin_dict(_get_page(conn))
        cookies = [
            _inventory_to_admin_dict(row)
            for row in conn.execute("SELECT * FROM cookies_inventory ORDER BY sort_order, name")
        ]
        sections = [
            _section_to_admin_dict(row)
            for row in conn.execute("SELECT * FROM cookies_sections ORDER BY sort_order, slug")
        ]
    return {"page": page, "cookies": cookies, "sections": sections}


def update_page(updates: dict) -> dict:
    """Patch editable Cookie Policy page-level text."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key not in _PAGE_FIELDS:
            raise CookiesValidationError(f"Field cannot be edited: {key}")
        fields[key] = _clean_text(value, required=key in _REQUIRED_PAGE_FIELDS)

    with get_db() as conn:
        _get_page(conn)
        if fields:
            set_clause = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(
                f"UPDATE cookies_page SET {set_clause} WHERE id = 'cookies'",  # noqa: S608
                list(fields.values()),
            )
        return _page_to_admin_dict(_get_page(conn))


def update_inventory_item(name: str, updates: dict) -> dict:
    """Patch editable cookie inventory text. The cookie name is immutable."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key not in _INVENTORY_FIELDS:
            raise CookiesValidationError(f"Field cannot be edited: {key}")
        fields[key] = _clean_text(value, required=key in _REQUIRED_INVENTORY_FIELDS)

    with get_db() as conn:
        _get_inventory_item(conn, name)
        if fields:
            set_clause = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(
                f"UPDATE cookies_inventory SET {set_clause} WHERE name = ?",  # noqa: S608
                [*fields.values(), name],
            )
        return _inventory_to_admin_dict(_get_inventory_item(conn, name))


def update_section(slug: str, updates: dict) -> dict:
    """Patch editable Cookie Policy section text. Slugs and order are immutable here."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key in _SECTION_TEXT_FIELDS:
            fields[key] = _clean_text(value, required=key in _REQUIRED_SECTION_FIELDS)
        elif key in _SECTION_ARRAY_FIELDS:
            fields[key] = _clean_lines(value, required=key in _REQUIRED_SECTION_FIELDS)
        else:
            raise CookiesValidationError(f"Field cannot be edited: {key}")

    with get_db() as conn:
        _get_section(conn, slug)
        if fields:
            set_clause = ", ".join(f"{key} = ?" for key in fields)
            conn.execute(
                f"UPDATE cookies_sections SET {set_clause} WHERE slug = ?",  # noqa: S608
                [*fields.values(), slug],
            )
        return _section_to_admin_dict(_get_section(conn, slug))
