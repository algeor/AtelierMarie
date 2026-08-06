"""Service and seed tests for admin-managed FAQ content."""

import pytest

from app.database import get_db
from app.services import faq_service
from app.services.faq_service import FaqSectionNotFoundError, FaqValidationError


@pytest.fixture(autouse=True)
def _restore_faq_seed(db):
    """Snapshot and restore FAQ seed tables around each test.

    ``faq_sections``/``faq_items`` are non-volatile seed tables (never truncated
    by ``_clean_tables``), so a test that edits or deletes seed rows would leak
    into siblings sharing the worker DB. Restore them to keep tests isolated.
    """
    with get_db() as conn:
        sections = conn.execute("SELECT * FROM faq_sections").fetchall()
        items = conn.execute("SELECT * FROM faq_items").fetchall()
    yield
    with get_db() as conn:
        conn.execute("DELETE FROM faq_items")
        conn.execute("DELETE FROM faq_sections")
        for table, rows in (("faq_sections", sections), ("faq_items", items)):
            if not rows:
                continue
            cols = list(rows[0].keys())
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))
            with conn.cursor() as cur:
                cur.executemany(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                    [tuple(row[c] for c in cols) for row in rows],
                )


def test_seed_runs_once_and_does_not_clobber_edits_or_deletions(db):
    with get_db() as conn:
        first_item_id = conn.execute(
            "SELECT id FROM faq_items ORDER BY section, sort_order LIMIT 1"
        ).fetchone()["id"]
        conn.execute("UPDATE faq_sections SET title_en = 'Edited title' WHERE slug = 'care'")
        conn.execute("DELETE FROM faq_items WHERE id = %s", (first_item_id,))

        assert conn.execute("SELECT COUNT(*) AS c FROM faq_sections").fetchone()["c"] == 4
        assert conn.execute("SELECT COUNT(*) AS c FROM faq_items").fetchone()["c"] == 21
        assert (
            conn.execute("SELECT title_en FROM faq_sections WHERE slug = 'care'").fetchone()[
                "title_en"
            ]
            == "Edited title"
        )
        assert (
            conn.execute(
                "SELECT 1 AS present FROM faq_items WHERE id = %s", (first_item_id,)
            ).fetchone()
            is None
        )


def test_public_locale_fallback_published_filter_and_unknown_locale(db):
    with get_db() as conn:
        item_id = conn.execute(
            "SELECT id FROM faq_items WHERE section = 'candles' ORDER BY sort_order LIMIT 1"
        ).fetchone()["id"]
        conn.execute(
            "UPDATE faq_items SET question_bg = 'BG question', answer_bg = NULL WHERE id = %s",
            (item_id,),
        )
        hidden_id = conn.execute(
            "SELECT id FROM faq_items WHERE section = 'candles' "
            "ORDER BY sort_order LIMIT 1 OFFSET 1"
        ).fetchone()["id"]
        conn.execute("UPDATE faq_items SET is_published = 0 WHERE id = %s", (hidden_id,))

    bg = faq_service.get_public_faq("bg")
    candles = next(section for section in bg["sections"] if section["slug"] == "candles")
    item = next(item for item in candles["items"] if item["id"] == item_id)
    assert item["question"] == "BG question"
    assert item["answer"].startswith("Yes. Every candle")
    assert hidden_id not in {item["id"] for item in candles["items"]}

    unknown = faq_service.get_public_faq("fr")
    candles_en = next(section for section in unknown["sections"] if section["slug"] == "candles")
    assert candles_en["title"] == "About Our Candles"


def test_seeded_section_anchor_is_preserved_when_empty(db):
    with get_db() as conn:
        conn.execute("UPDATE faq_items SET is_published = 0 WHERE section = 'shipping'")

    faq = faq_service.get_public_faq("en")
    shipping = next(section for section in faq["sections"] if section["slug"] == "shipping")
    assert shipping["items"] == []


def test_seeded_returns_faq_mentions_uncollected_parcels_and_terms_link(db):
    en = faq_service.get_public_faq("en")
    shipping_en = next(section for section in en["sections"] if section["slug"] == "shipping")
    returns_en = next(
        item for item in shipping_en["items"] if item["question"] == "Do you accept returns?"
    )
    assert "Uncollected or refused courier parcels" in returns_en["answer"]
    assert "(/en/terms#returns)" in returns_en["answer"]

    bg = faq_service.get_public_faq("bg")
    shipping_bg = next(section for section in bg["sections"] if section["slug"] == "shipping")
    returns_bg = next(
        item for item in shipping_bg["items"] if item["question"] == "Приемате ли връщания?"
    )
    assert "Непотърсените или отказани куриерски пратки" in returns_bg["answer"]
    assert "(/bg/terms#returns)" in returns_bg["answer"]


def test_admin_crud_raw_storage_publish_reorder_and_section_update(db):
    raw_answer = "We'd use Care & Safety—always.\n\n- First line"
    item = faq_service.create_item(
        {
            "section": "care",
            "question_en": "Can I test raw text?",
            "answer_en": raw_answer,
            "question_bg": None,
            "answer_bg": None,
        }
    )
    assert item["is_published"] is True

    with get_db() as conn:
        stored = conn.execute(
            "SELECT answer_en FROM faq_items WHERE id = %s", (item["id"],)
        ).fetchone()["answer_en"]
    assert stored == raw_answer

    updated = faq_service.update_item(item["id"], {"answer_bg": "BG answer", "is_published": False})
    assert updated["answer_bg"] == "BG answer"
    assert updated["is_published"] is False

    faq_service.set_published(item["id"], True)
    before = faq_service.list_faq_admin()
    care_ids = [
        item["id"]
        for section in before["sections"]
        if section["slug"] == "care"
        for item in section["items"]
    ]
    faq_service.reorder_items("care", list(reversed(care_ids)))
    after = faq_service.list_faq_admin()
    reordered = next(section for section in after["sections"] if section["slug"] == "care")
    assert [item["id"] for item in reordered["items"]] == list(reversed(care_ids))

    section = faq_service.update_section(
        "care", {"title_bg": "Нова грижа", "sort_order": 9, "slug": "changed"}
    )
    assert section["slug"] == "care"
    assert section["title_bg"] == "Нова грижа"
    assert section["sort_order"] == 9

    faq_service.delete_item(item["id"])
    admin = faq_service.list_faq_admin()
    assert item["id"] not in {
        faq_item["id"] for section in admin["sections"] for faq_item in section["items"]
    }


def test_unknown_section_rejected(db):
    with pytest.raises(FaqSectionNotFoundError):
        faq_service.create_item({"section": "missing", "question_en": "Q", "answer_en": "A"})
    with pytest.raises(FaqValidationError):
        faq_service.reorder_items(
            "care",
            [
                next(
                    item["id"]
                    for section in faq_service.list_faq_admin()["sections"]
                    if section["slug"] == "candles"
                    for item in section["items"]
                )
            ],
        )
