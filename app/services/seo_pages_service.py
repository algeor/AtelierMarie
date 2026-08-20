"""Service layer for admin-managed SEO landing pages."""

import json

from app.database import DbConnection, get_db
from app.models.terms import MAX_TERMS_TEXT_LENGTH

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_ts(value: object) -> str | None:
    from datetime import datetime

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


class SeoLandingPageNotFoundError(Exception):
    """Raised when a SEO landing page or FAQ item does not exist."""


class SeoLandingPageValidationError(Exception):
    """Raised for invalid SEO landing page content."""


_PAGE_TEXT_FIELDS = {
    "meta_title_en",
    "meta_title_bg",
    "meta_description_en",
    "meta_description_bg",
    "eyebrow_en",
    "eyebrow_bg",
    "title_en",
    "title_bg",
    "intro_en",
    "intro_bg",
    "note_en",
    "note_bg",
    "shop_all_label_en",
    "shop_all_label_bg",
    "section_title_en",
    "section_title_bg",
    "empty_text_en",
    "empty_text_bg",
    "benefits_title_en",
    "benefits_title_bg",
    "faq_title_en",
    "faq_title_bg",
}
_PAGE_ARRAY_FIELDS = {"benefits_en", "benefits_bg"}
_PAGE_BOOL_FIELDS = {"is_published"}
_REQUIRED_PAGE_FIELDS = {field for field in _PAGE_TEXT_FIELDS if field.endswith("_en")} | {
    "benefits_en"
}
_FAQ_TEXT_FIELDS = {"question_en", "question_bg", "answer_en", "answer_bg"}
_FAQ_BOOL_FIELDS = {"is_published"}
_REQUIRED_FAQ_FIELDS = {"question_en", "answer_en"}


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


def _localized_text(row: dict, field: str, locale: str) -> str:
    bg = row[f"{field}_bg"]
    if locale == "bg" and bg:
        return bg
    return row[f"{field}_en"]


def _localized_lines(row: dict, field: str, locale: str) -> list[str]:
    en = _json_lines(row[f"{field}_en"]) or []
    bg = _json_lines(row[f"{field}_bg"])
    if locale == "bg" and bg:
        return bg
    return en


def _clean_text(value: str | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise SeoLandingPageValidationError("Required text cannot be null")
        return None
    stripped = value.strip()
    if not stripped:
        if required:
            raise SeoLandingPageValidationError("Required text cannot be blank")
        return None
    return stripped


def _clean_lines(value: list[str] | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise SeoLandingPageValidationError("Required list cannot be null")
        return None
    lines = [str(line).strip() for line in value if str(line).strip()]
    if not lines:
        if required:
            raise SeoLandingPageValidationError("Required list cannot be blank")
        return None
    if any(len(line) > MAX_TERMS_TEXT_LENGTH for line in lines):
        raise SeoLandingPageValidationError("A list item is too long")
    return json.dumps(lines, ensure_ascii=False)


def _page_admin_dict(row: dict) -> dict:
    return {
        "slug": row["slug"],
        "product_type": row["product_type"],
        "path_en": row["path_en"],
        "path_bg": row["path_bg"],
        "meta_title_en": row["meta_title_en"],
        "meta_title_bg": row["meta_title_bg"],
        "meta_description_en": row["meta_description_en"],
        "meta_description_bg": row["meta_description_bg"],
        "eyebrow_en": row["eyebrow_en"],
        "eyebrow_bg": row["eyebrow_bg"],
        "title_en": row["title_en"],
        "title_bg": row["title_bg"],
        "intro_en": row["intro_en"],
        "intro_bg": row["intro_bg"],
        "note_en": row["note_en"],
        "note_bg": row["note_bg"],
        "shop_all_label_en": row["shop_all_label_en"],
        "shop_all_label_bg": row["shop_all_label_bg"],
        "section_title_en": row["section_title_en"],
        "section_title_bg": row["section_title_bg"],
        "empty_text_en": row["empty_text_en"],
        "empty_text_bg": row["empty_text_bg"],
        "benefits_title_en": row["benefits_title_en"],
        "benefits_title_bg": row["benefits_title_bg"],
        "faq_title_en": row["faq_title_en"],
        "faq_title_bg": row["faq_title_bg"],
        "benefits_en": _json_lines(row["benefits_en"]) or [],
        "benefits_bg": _json_lines(row["benefits_bg"]),
        "is_published": bool(row["is_published"]),
        "created_at": _fmt_ts(row["created_at"]),
        "updated_at": _fmt_ts(row["updated_at"]),
        "faq": [],
    }


def _faq_admin_dict(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "page_slug": row["page_slug"],
        "question_en": row["question_en"],
        "question_bg": row["question_bg"],
        "answer_en": row["answer_en"],
        "answer_bg": row["answer_bg"],
        "sort_order": int(row["sort_order"]),
        "is_published": bool(row["is_published"]),
        "created_at": _fmt_ts(row["created_at"]),
        "updated_at": _fmt_ts(row["updated_at"]),
    }


def _get_page(conn: DbConnection, slug: str) -> dict:
    row = conn.execute("SELECT * FROM seo_landing_pages WHERE slug = %s", (slug,)).fetchone()
    if row is None:
        raise SeoLandingPageNotFoundError(f"SEO landing page not found: {slug}")
    return row


def _get_faq(conn: DbConnection, page_slug: str, item_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM seo_landing_faq_items WHERE page_slug = %s AND id = %s",
        (page_slug, item_id),
    ).fetchone()
    if row is None:
        raise SeoLandingPageNotFoundError(f"SEO landing FAQ item not found: {item_id}")
    return row


def get_public_page(slug: str, locale: str | None = "en") -> dict:
    """Return localized SEO landing page content."""
    resolved = _public_locale(locale)
    with get_db() as conn:
        page = _get_page(conn, slug)
        if not bool(page["is_published"]):
            raise SeoLandingPageNotFoundError(f"SEO landing page not published: {slug}")
        faq_rows = conn.execute(
            """
            SELECT * FROM seo_landing_faq_items
            WHERE page_slug = %s AND is_published = 1
            ORDER BY sort_order, id
            """,
            (slug,),
        ).fetchall()

    return {
        "slug": page["slug"],
        "product_type": page["product_type"],
        "path": page[f"path_{resolved}"],
        "meta_title": _localized_text(page, "meta_title", resolved),
        "meta_description": _localized_text(page, "meta_description", resolved),
        "eyebrow": _localized_text(page, "eyebrow", resolved),
        "title": _localized_text(page, "title", resolved),
        "intro": _localized_text(page, "intro", resolved),
        "note": _localized_text(page, "note", resolved),
        "shop_all_label": _localized_text(page, "shop_all_label", resolved),
        "section_title": _localized_text(page, "section_title", resolved),
        "empty_text": _localized_text(page, "empty_text", resolved),
        "benefits_title": _localized_text(page, "benefits_title", resolved),
        "benefits": _localized_lines(page, "benefits", resolved),
        "faq_title": _localized_text(page, "faq_title", resolved),
        "faq": [
            {
                "id": int(row["id"]),
                "question": _localized_text(row, "question", resolved),
                "answer": _localized_text(row, "answer", resolved),
            }
            for row in faq_rows
        ],
    }


def list_admin_pages() -> dict:
    """Return all raw bilingual SEO landing pages for admin editing."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM seo_landing_pages ORDER BY slug").fetchall()
        pages = [_page_admin_dict(row) for row in rows]
        by_slug = {page["slug"]: page for page in pages}
        faq_rows = conn.execute(
            "SELECT * FROM seo_landing_faq_items ORDER BY page_slug, sort_order, id"
        ).fetchall()
        for row in faq_rows:
            page = by_slug.get(row["page_slug"])
            if page is not None:
                page["faq"].append(_faq_admin_dict(row))
    return {"pages": pages}


def update_page(slug: str, updates: dict) -> dict:
    """Patch editable SEO landing page fields."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key in _PAGE_TEXT_FIELDS:
            fields[key] = _clean_text(value, required=key in _REQUIRED_PAGE_FIELDS)
        elif key in _PAGE_ARRAY_FIELDS:
            fields[key] = _clean_lines(value, required=key in _REQUIRED_PAGE_FIELDS)
        elif key in _PAGE_BOOL_FIELDS:
            fields[key] = 1 if value else 0
        else:
            raise SeoLandingPageValidationError(f"Field cannot be edited: {key}")

    with get_db() as conn:
        _get_page(conn, slug)
        if fields:
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE seo_landing_pages SET {set_clause} WHERE slug = %s",  # noqa: S608
                [*fields.values(), slug],
            )
    return next(page for page in list_admin_pages()["pages"] if page["slug"] == slug)


def update_faq_item(page_slug: str, item_id: int, updates: dict) -> dict:
    """Patch editable SEO landing FAQ fields."""
    fields: dict[str, object | None] = {}
    for key, value in updates.items():
        if key in _FAQ_TEXT_FIELDS:
            fields[key] = _clean_text(value, required=key in _REQUIRED_FAQ_FIELDS)
        elif key in _FAQ_BOOL_FIELDS:
            fields[key] = 1 if value else 0
        else:
            raise SeoLandingPageValidationError(f"Field cannot be edited: {key}")

    with get_db() as conn:
        _get_page(conn, page_slug)
        _get_faq(conn, page_slug, item_id)
        if fields:
            set_clause = ", ".join(f"{key} = %s" for key in fields)
            conn.execute(
                f"UPDATE seo_landing_faq_items SET {set_clause} WHERE page_slug = %s AND id = %s",  # noqa: S608
                [*fields.values(), page_slug, item_id],
            )
        return _faq_admin_dict(_get_faq(conn, page_slug, item_id))
