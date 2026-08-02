"""Service layer for admin-managed Cookie Policy content."""

import json
import sqlite3
from datetime import UTC, datetime

from app.config import get_settings
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
        "source": row["source"],
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
        "last_audited_at": row["last_audited_at"],
        "observed_on": _json_lines(row["observed_on"]) or [],
        "is_active": bool(row["is_active"]),
        "auto_detected": bool(row["auto_detected"]),
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
    row = conn.execute("SELECT * FROM cookies_inventory WHERE name = %s", (name,)).fetchone()
    if row is None:
        raise CookiesNotFoundError(f"Cookie inventory row not found: {name}")
    return row


def _get_section(conn: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cookies_sections WHERE slug = %s", (slug,)).fetchone()
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


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _duration_text(seconds: int) -> tuple[str, str]:
    days = max(1, round(seconds / 86_400))
    return (f"Up to {days} days.", f"До {days} дни.")


def default_detected_inventory() -> list[dict]:
    """Return app-owned cookies that may not appear in an anonymous crawl."""
    settings = get_settings()
    session_duration_en, session_duration_bg = _duration_text(settings.session_max_age)
    auth_duration_en, auth_duration_bg = _duration_text(settings.jwt_expiry_hours * 3600)
    return [
        {
            "name": settings.session_cookie_name,
            "purpose_en": "Keeps cart, checkout, language, and session continuity for the visitor.",
            "purpose_bg": "Пази кошницата, поръчката, езика и сесията на посетителя.",
            "type_en": "Necessary HttpOnly session cookie",
            "type_bg": "Необходим HttpOnly session cookie",
            "duration_en": session_duration_en,
            "duration_bg": session_duration_bg,
            "source": "app_registry",
        },
        {
            "name": settings.jwt_cookie_name,
            "purpose_en": "Keeps a signed-in account or admin session active after login.",
            "purpose_bg": "Поддържа активен вход в профил или админ сесия след логин.",
            "type_en": "Necessary HttpOnly authentication cookie",
            "type_bg": "Необходим HttpOnly authentication cookie",
            "duration_en": auth_duration_en,
            "duration_bg": auth_duration_bg,
            "source": "app_registry",
        },
        {
            "name": "NEXT_LOCALE",
            "purpose_en": "Stores the selected storefront language.",
            "purpose_bg": "Запазва избрания език на магазина.",
            "type_en": "Preference cookie",
            "type_bg": "Cookie за предпочитание",
            "duration_en": "Up to 1 year.",
            "duration_bg": "До 1 година.",
            "source": "app_registry",
        },
        {
            "name": "atelier_cookie_consent",
            "purpose_en": "Stores the visitor's cookie and analytics consent choice.",
            "purpose_bg": "Запазва избора на посетителя за бисквитки и аналитика.",
            "type_en": "Consent preference cookie",
            "type_bg": "Cookie за съгласие",
            "duration_en": "Up to 1 year.",
            "duration_bg": "До 1 година.",
            "source": "app_registry",
        },
    ]


def sync_detected_inventory(
    items: list[dict], *, source: str = "deploy_audit", deactivate_missing: bool = True
) -> list[dict]:
    """Upsert cookie inventory rows discovered by a deploy/browser audit."""
    audited_at = _now()
    cleaned: dict[str, dict] = {}
    for item in items:
        name = _clean_text(item.get("name"), required=True)
        if name is None:
            continue
        purpose_en = _clean_text(
            item.get("purpose_en") or "Detected by the deployment cookie audit.",
            required=True,
        )
        type_en = _clean_text(item.get("type_en") or "Detected browser storage", required=True)
        duration_en = _clean_text(
            item.get("duration_en") or "Until expiry or browser clearing.", required=True
        )
        observed_on = item.get("observed_on")
        if isinstance(observed_on, str):
            observed_lines = [observed_on]
        elif isinstance(observed_on, list):
            observed_lines = [str(value).strip() for value in observed_on if str(value).strip()]
        else:
            observed_lines = []
        cleaned[name] = {
            "name": name,
            "purpose_en": purpose_en,
            "purpose_bg": _clean_text(item.get("purpose_bg"), required=False),
            "type_en": type_en,
            "type_bg": _clean_text(item.get("type_bg"), required=False),
            "duration_en": duration_en,
            "duration_bg": _clean_text(item.get("duration_bg"), required=False),
            "source": _clean_text(item.get("source") or source, required=True),
            "observed_on": json.dumps(sorted(set(observed_lines)), ensure_ascii=False),
        }

    with get_db() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM cookies_inventory"
        ).fetchone()[0]
        next_order = int(max_order) + 1
        for row in cleaned.values():
            existing = conn.execute(
                "SELECT sort_order FROM cookies_inventory WHERE name = %s", (row["name"],)
            ).fetchone()
            sort_order = existing["sort_order"] if existing else next_order
            if existing is None:
                next_order += 1
            conn.execute(
                """
                INSERT INTO cookies_inventory (
                    name, purpose_en, purpose_bg, type_en, type_bg, duration_en, duration_bg,
                    source, first_seen_at, last_seen_at, last_audited_at, observed_on,
                    is_active, auto_detected, sort_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 1, %s)
                ON CONFLICT(name) DO UPDATE SET
                    purpose_en = excluded.purpose_en,
                    purpose_bg = COALESCE(excluded.purpose_bg, cookies_inventory.purpose_bg),
                    type_en = excluded.type_en,
                    type_bg = COALESCE(excluded.type_bg, cookies_inventory.type_bg),
                    duration_en = excluded.duration_en,
                    duration_bg = COALESCE(excluded.duration_bg, cookies_inventory.duration_bg),
                    source = excluded.source,
                    first_seen_at = COALESCE(
                        cookies_inventory.first_seen_at, excluded.first_seen_at
                    ),
                    last_seen_at = excluded.last_seen_at,
                    last_audited_at = excluded.last_audited_at,
                    observed_on = excluded.observed_on,
                    is_active = 1,
                    auto_detected = 1,
                    sort_order = cookies_inventory.sort_order
                """,
                (
                    row["name"],
                    row["purpose_en"],
                    row["purpose_bg"],
                    row["type_en"],
                    row["type_bg"],
                    row["duration_en"],
                    row["duration_bg"],
                    row["source"],
                    audited_at,
                    audited_at,
                    audited_at,
                    row["observed_on"],
                    sort_order,
                ),
            )
        if deactivate_missing and cleaned:
            placeholders = ", ".join("%s" for _ in cleaned)
            conn.execute(
                f"""
                UPDATE cookies_inventory
                SET is_active = 0, last_audited_at = %s
                WHERE auto_detected = 1 AND name NOT IN ({placeholders})
                """,  # noqa: S608
                [audited_at, *cleaned.keys()],
            )
        return [
            _inventory_to_admin_dict(row)
            for row in conn.execute("SELECT * FROM cookies_inventory ORDER BY sort_order, name")
        ]


def get_public_cookies(locale: str | None = "en") -> dict:
    """Return localized Cookie Policy content for the storefront."""
    resolved = _public_locale(locale)
    with get_db() as conn:
        page = _get_page(conn)
        inventory_rows = conn.execute(
            "SELECT * FROM cookies_inventory WHERE is_active = 1 ORDER BY sort_order, name"
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
            set_clause = ", ".join(f"{key} = %s" for key in fields)
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
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE cookies_inventory SET {set_clause} WHERE name = %s",  # noqa: S608
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
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE cookies_sections SET {set_clause} WHERE slug = %s",  # noqa: S608
                [*fields.values(), slug],
            )
        return _section_to_admin_dict(_get_section(conn, slug))
