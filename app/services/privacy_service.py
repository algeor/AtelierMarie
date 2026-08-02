"""Service layer for admin-managed Privacy Policy content."""

import json
import sqlite3

from app.database import get_db
from app.models.privacy import MAX_PRIVACY_TEXT_LENGTH


class PrivacyNotFoundError(Exception):
    """Raised when the Privacy Policy singleton row or a section is missing."""


class PrivacyValidationError(Exception):
    """Raised for invalid editable Privacy Policy content."""


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
    "controller_title_en",
    "controller_title_bg",
}
_REQUIRED_PAGE_FIELDS = {field for field in _PAGE_FIELDS if field.endswith("_en")}

_SECTION_TEXT_FIELDS = {"title_en", "title_bg", "nav_en", "nav_bg"}
_SECTION_ARRAY_FIELDS = {"body_en", "body_bg"}
_REQUIRED_SECTION_FIELDS = {"title_en", "nav_en", "body_en"}


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
        "controller_title_en": row["controller_title_en"],
        "controller_title_bg": row["controller_title_bg"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _section_to_admin_dict(row: sqlite3.Row) -> dict:
    return {
        "slug": row["slug"],
        "title_en": row["title_en"],
        "title_bg": row["title_bg"],
        "nav_en": row["nav_en"],
        "nav_bg": row["nav_bg"],
        "body_en": _json_lines(row["body_en"]) or [],
        "body_bg": _json_lines(row["body_bg"]),
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_page(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM privacy_page WHERE id = 'privacy'").fetchone()
    if row is None:
        raise PrivacyNotFoundError("Privacy Policy page not found")
    return row


def _get_section(conn: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM privacy_sections WHERE slug = %s", (slug,)).fetchone()
    if row is None:
        raise PrivacyNotFoundError(f"Privacy Policy section not found: {slug}")
    return row


def _clean_text(value: str | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise PrivacyValidationError("Required text cannot be null")
        return None
    stripped = value.strip()
    if not stripped:
        if required:
            raise PrivacyValidationError("Required text cannot be blank")
        return None
    return stripped


def _clean_lines(value: list[str] | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise PrivacyValidationError("Required section body cannot be null")
        return None
    lines = [str(line).strip() for line in value if str(line).strip()]
    if not lines:
        if required:
            raise PrivacyValidationError("Required section body cannot be blank")
        return None
    if any(len(line) > MAX_PRIVACY_TEXT_LENGTH for line in lines):
        raise PrivacyValidationError("A Privacy Policy paragraph is too long")
    return json.dumps(lines, ensure_ascii=False)


def get_public_privacy(locale: str | None = "en") -> dict:
    """Return localized Privacy Policy content for the storefront."""
    resolved = _public_locale(locale)
    with get_db() as conn:
        page = _get_page(conn)
        section_rows = conn.execute(
            "SELECT * FROM privacy_sections ORDER BY sort_order, slug"
        ).fetchall()

    return {
        "meta_title": _localized_text(page, "meta_title", resolved),
        "meta_description": _localized_text(page, "meta_description", resolved),
        "eyebrow": _localized_text(page, "eyebrow", resolved),
        "title": _localized_text(page, "title", resolved),
        "subtitle": _localized_text(page, "subtitle", resolved),
        "last_updated": _localized_text(page, "last_updated", resolved),
        "controller_title": _localized_text(page, "controller_title", resolved),
        "sections": [
            {
                "id": row["slug"],
                "title": _localized_text(row, "title", resolved),
                "nav": _localized_text(row, "nav", resolved),
                "body": _localized_lines(row, "body", resolved),
            }
            for row in section_rows
        ],
    }


def list_admin_privacy() -> dict:
    """Return raw bilingual Privacy Policy content for admin editing."""
    with get_db() as conn:
        page = _page_to_admin_dict(_get_page(conn))
        sections = [
            _section_to_admin_dict(row)
            for row in conn.execute("SELECT * FROM privacy_sections ORDER BY sort_order, slug")
        ]
    return {"page": page, "sections": sections}


def update_page(updates: dict) -> dict:
    """Patch editable page-level Privacy Policy text."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key not in _PAGE_FIELDS:
            raise PrivacyValidationError(f"Field cannot be edited: {key}")
        fields[key] = _clean_text(value, required=key in _REQUIRED_PAGE_FIELDS)

    with get_db() as conn:
        _get_page(conn)
        if fields:
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE privacy_page SET {set_clause} WHERE id = 'privacy'",  # noqa: S608
                list(fields.values()),
            )
        return _page_to_admin_dict(_get_page(conn))


def update_section(slug: str, updates: dict) -> dict:
    """Patch editable section text. Slugs and order are immutable here."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key in _SECTION_TEXT_FIELDS:
            fields[key] = _clean_text(value, required=key in _REQUIRED_SECTION_FIELDS)
        elif key in _SECTION_ARRAY_FIELDS:
            fields[key] = _clean_lines(value, required=key in _REQUIRED_SECTION_FIELDS)
        else:
            raise PrivacyValidationError(f"Field cannot be edited: {key}")

    with get_db() as conn:
        _get_section(conn, slug)
        if fields:
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE privacy_sections SET {set_clause} WHERE slug = %s",  # noqa: S608
                [*fields.values(), slug],
            )
        return _section_to_admin_dict(_get_section(conn, slug))
