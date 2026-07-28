"""Service and seed tests for admin-managed FAQ content."""

import sqlite3

import pytest

from app.database import get_db, init_db
from app.services import faq_service
from app.services.faq_service import FaqSectionNotFoundError, FaqValidationError


@pytest.fixture()
def faq_db(tmp_path) -> str:
    """Fresh seeded DB for each FAQ service test."""
    path = str(tmp_path / "faq.db")
    init_db(path)
    return path


def test_seed_runs_once_and_does_not_clobber_edits_or_deletions(tmp_path):
    path = str(tmp_path / "seed.db")
    init_db(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    first_item_id = conn.execute(
        "SELECT id FROM faq_items ORDER BY section, sort_order LIMIT 1"
    ).fetchone()["id"]
    conn.execute("UPDATE faq_sections SET title_en = 'Edited title' WHERE slug = 'care'")
    conn.execute("DELETE FROM faq_items WHERE id = ?", (first_item_id,))
    conn.commit()
    conn.close()

    init_db(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    assert conn.execute("SELECT COUNT(*) AS c FROM faq_sections").fetchone()["c"] == 4
    assert conn.execute("SELECT COUNT(*) AS c FROM faq_items").fetchone()["c"] == 21
    assert (
        conn.execute("SELECT title_en FROM faq_sections WHERE slug = 'care'").fetchone()[0]
        == "Edited title"
    )
    assert conn.execute("SELECT 1 FROM faq_items WHERE id = ?", (first_item_id,)).fetchone() is None
    conn.close()


def test_public_locale_fallback_published_filter_and_unknown_locale(faq_db):
    with get_db() as conn:
        item_id = conn.execute(
            "SELECT id FROM faq_items WHERE section = 'candles' ORDER BY sort_order LIMIT 1"
        ).fetchone()["id"]
        conn.execute(
            "UPDATE faq_items SET question_bg = 'BG question', answer_bg = NULL WHERE id = ?",
            (item_id,),
        )
        hidden_id = conn.execute(
            "SELECT id FROM faq_items WHERE section = 'candles' "
            "ORDER BY sort_order LIMIT 1 OFFSET 1"
        ).fetchone()["id"]
        conn.execute("UPDATE faq_items SET is_published = 0 WHERE id = ?", (hidden_id,))

    bg = faq_service.get_public_faq("bg")
    candles = next(section for section in bg["sections"] if section["slug"] == "candles")
    item = next(item for item in candles["items"] if item["id"] == item_id)
    assert item["question"] == "BG question"
    assert item["answer"].startswith("Yes. Every candle")
    assert hidden_id not in {item["id"] for item in candles["items"]}

    unknown = faq_service.get_public_faq("fr")
    candles_en = next(section for section in unknown["sections"] if section["slug"] == "candles")
    assert candles_en["title"] == "About Our Candles"


def test_seeded_section_anchor_is_preserved_when_empty(faq_db):
    with get_db() as conn:
        conn.execute("UPDATE faq_items SET is_published = 0 WHERE section = 'shipping'")

    faq = faq_service.get_public_faq("en")
    shipping = next(section for section in faq["sections"] if section["slug"] == "shipping")
    assert shipping["items"] == []


def test_admin_crud_raw_storage_publish_reorder_and_section_update(faq_db):
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
            "SELECT answer_en FROM faq_items WHERE id = ?", (item["id"],)
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


def test_unknown_section_rejected(faq_db):
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
