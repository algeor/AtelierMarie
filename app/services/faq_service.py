"""FAQ service layer for public and admin-managed FAQ content."""

import sqlite3
from typing import Any

from app.database import get_db


class FaqItemNotFoundError(Exception):
    """Raised when an FAQ item id does not exist."""


class FaqSectionNotFoundError(Exception):
    """Raised when an FAQ section slug does not exist."""


class FaqValidationError(Exception):
    """Raised when an FAQ mutation is invalid."""


def _public_locale(locale: str | None) -> str:
    return "bg" if locale == "bg" else "en"


def _section_exists(conn: sqlite3.Connection, slug: str) -> bool:
    row = conn.execute("SELECT 1 FROM faq_sections WHERE slug = ?", (slug,)).fetchone()
    return row is not None


def _item_to_admin_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "section": row["section"],
        "question_en": row["question_en"],
        "question_bg": row["question_bg"],
        "answer_en": row["answer_en"],
        "answer_bg": row["answer_bg"],
        "sort_order": row["sort_order"],
        "is_published": bool(row["is_published"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _section_to_admin_dict(row: sqlite3.Row) -> dict:
    return {
        "slug": row["slug"],
        "title_en": row["title_en"],
        "title_bg": row["title_bg"],
        "icon": row["icon"],
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "items": [],
    }


def _get_admin_item(conn: sqlite3.Connection, item_id: int) -> dict:
    row = conn.execute("SELECT * FROM faq_items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise FaqItemNotFoundError(f"FAQ item not found: {item_id}")
    return _item_to_admin_dict(row)


def get_public_faq(locale: str | None = "en") -> dict:
    """Return published FAQ content grouped by section and localized.

    The four seeded sections are returned even when they currently have no
    published items, preserving stable deep-link anchors such as `#care`.
    """
    resolved = _public_locale(locale)
    with get_db() as conn:
        section_rows = conn.execute(
            """
            SELECT slug, title_en, title_bg, icon
            FROM faq_sections
            ORDER BY sort_order, slug
            """
        ).fetchall()
        item_rows = conn.execute(
            """
            SELECT id, section, question_en, question_bg, answer_en, answer_bg
            FROM faq_items
            WHERE is_published = 1
            ORDER BY section, sort_order, id
            """
        ).fetchall()

    sections: list[dict[str, Any]] = []
    by_slug: dict[str, dict[str, Any]] = {}
    for row in section_rows:
        title = row["title_bg"] or row["title_en"] if resolved == "bg" else row["title_en"]
        section_data = {
            "slug": row["slug"],
            "title": title,
            "icon": row["icon"],
            "items": [],
        }
        by_slug[row["slug"]] = section_data
        sections.append(section_data)

    for row in item_rows:
        target_section = by_slug.get(row["section"])
        if target_section is None:
            continue
        question = (
            row["question_bg"] or row["question_en"] if resolved == "bg" else row["question_en"]
        )
        answer = row["answer_bg"] or row["answer_en"] if resolved == "bg" else row["answer_en"]
        target_section["items"].append({"id": row["id"], "question": question, "answer": answer})

    return {"sections": sections}


def list_faq_admin() -> dict:
    """Return all sections with all FAQ items, including unpublished ones."""
    with get_db() as conn:
        section_rows = conn.execute(
            "SELECT * FROM faq_sections ORDER BY sort_order, slug"
        ).fetchall()
        item_rows = conn.execute(
            "SELECT * FROM faq_items ORDER BY section, sort_order, id"
        ).fetchall()

    sections: list[dict[str, Any]] = []
    by_slug: dict[str, dict[str, Any]] = {}
    for row in section_rows:
        section_data = _section_to_admin_dict(row)
        by_slug[section_data["slug"]] = section_data
        sections.append(section_data)

    for row in item_rows:
        target_section = by_slug.get(row["section"])
        if target_section is not None:
            target_section["items"].append(_item_to_admin_dict(row))

    return {"sections": sections}


def create_item(data: dict) -> dict:
    """Create an FAQ item with trusted raw plain text."""
    section = data["section"]
    with get_db() as conn:
        if not _section_exists(conn, section):
            raise FaqSectionNotFoundError(f"FAQ section not found: {section}")
        sort_order = data.get("sort_order")
        if sort_order is None:
            row = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order "
                "FROM faq_items WHERE section = ?",
                (section,),
            ).fetchone()
            sort_order = row["next_order"]
        cursor = conn.execute(
            """
            INSERT INTO faq_items (
                section, question_en, question_bg, answer_en, answer_bg, sort_order, is_published
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                section,
                data["question_en"],
                data.get("question_bg"),
                data["answer_en"],
                data.get("answer_bg"),
                sort_order,
            ),
        )
        item_id = cursor.lastrowid
        if item_id is None:
            raise RuntimeError("FAQ item insert did not return an id")
        return _get_admin_item(conn, item_id)


def update_item(item_id: int, updates: dict) -> dict:
    """Update editable FAQ item fields. Section changes must target an existing section."""
    allowed = {
        "section",
        "question_en",
        "question_bg",
        "answer_en",
        "answer_bg",
        "sort_order",
        "is_published",
    }
    fields = {k: v for k, v in updates.items() if k in allowed}
    if "is_published" in fields:
        fields["is_published"] = 1 if fields["is_published"] else 0

    with get_db() as conn:
        if conn.execute("SELECT 1 FROM faq_items WHERE id = ?", (item_id,)).fetchone() is None:
            raise FaqItemNotFoundError(f"FAQ item not found: {item_id}")
        if "section" in fields and not _section_exists(conn, fields["section"]):
            raise FaqSectionNotFoundError(f"FAQ section not found: {fields['section']}")
        if fields:
            set_clause = ", ".join(f"{name} = ?" for name in fields)
            conn.execute(
                f"UPDATE faq_items SET {set_clause} WHERE id = ?",  # noqa: S608
                [*fields.values(), item_id],
            )
        return _get_admin_item(conn, item_id)


def delete_item(item_id: int) -> None:
    """Delete an FAQ item permanently."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM faq_items WHERE id = ?", (item_id,))
        if cursor.rowcount == 0:
            raise FaqItemNotFoundError(f"FAQ item not found: {item_id}")


def set_published(item_id: int, published: bool) -> dict:
    """Toggle an FAQ item's public visibility."""
    return update_item(item_id, {"is_published": published})


def reorder_items(section: str, ordered_ids: list[int]) -> dict:
    """Persist item order within a section."""
    with get_db() as conn:
        if not _section_exists(conn, section):
            raise FaqSectionNotFoundError(f"FAQ section not found: {section}")
        if len(ordered_ids) != len(set(ordered_ids)):
            raise FaqValidationError("ordered_ids must not contain duplicates")
        if ordered_ids:
            placeholders = ", ".join("?" for _ in ordered_ids)
            rows = conn.execute(
                f"SELECT id, section FROM faq_items WHERE id IN ({placeholders})",  # noqa: S608
                ordered_ids,
            ).fetchall()
            found = {row["id"]: row["section"] for row in rows}
            missing = [item_id for item_id in ordered_ids if item_id not in found]
            wrong_section = [
                item_id for item_id, item_section in found.items() if item_section != section
            ]
            if missing:
                raise FaqItemNotFoundError(f"FAQ item not found: {missing[0]}")
            if wrong_section:
                raise FaqValidationError("Cannot reorder items outside the target section")
        for sort_order, item_id in enumerate(ordered_ids):
            conn.execute(
                "UPDATE faq_items SET sort_order = ? WHERE id = ? AND section = ?",
                (sort_order, item_id, section),
            )
    return list_faq_admin()


def update_section(slug: str, updates: dict) -> dict:
    """Update section display fields. Slugs are immutable."""
    allowed = {"title_en", "title_bg", "icon", "sort_order"}
    fields = {k: v for k, v in updates.items() if k in allowed}

    with get_db() as conn:
        if not _section_exists(conn, slug):
            raise FaqSectionNotFoundError(f"FAQ section not found: {slug}")
        if fields:
            set_clause = ", ".join(f"{name} = ?" for name in fields)
            conn.execute(
                f"UPDATE faq_sections SET {set_clause} WHERE slug = ?",  # noqa: S608
                [*fields.values(), slug],
            )
    return next(section for section in list_faq_admin()["sections"] if section["slug"] == slug)
