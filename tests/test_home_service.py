"""Service tests for editable homepage content."""

import pytest

from app.database import get_db
from app.services import home_service
from app.services.home_service import HomeReorderError, HomeValidationError
from tests.conftest import R2_TEST_PUBLIC_BASE


def test_seed_has_expected_home_sections_and_items(db):
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM home_sections").fetchone()["n"] == 4
        assert conn.execute("SELECT COUNT(*) AS n FROM home_items").fetchone()["n"] == 4


def test_public_home_filters_unpublished_sections_and_items(db):
    with get_db() as conn:
        conn.execute("UPDATE home_sections SET is_published = 0 WHERE slug = 'categories'")
        first_item = conn.execute(
            "SELECT id FROM home_items WHERE section = 'trust' ORDER BY sort_order LIMIT 1"
        ).fetchone()["id"]
        conn.execute("UPDATE home_items SET is_published = 0 WHERE id = %s", (first_item,))

    sections = home_service.get_public_home()["sections"]
    assert "categories" not in [section["slug"] for section in sections]
    trust = next(section for section in sections if section["slug"] == "trust")
    assert all(item["title"] != "Handmade slowly" for item in trust["items"])


def test_bg_locale_falls_back_to_english(db):
    with get_db() as conn:
        conn.execute("UPDATE home_sections SET heading_bg = NULL WHERE slug = 'hero'")

    hero = home_service.get_public_home("bg")["sections"][0]
    assert hero["heading"] == "Atelier Marie"


def test_public_home_reconstructs_r2_image_urls(db, fake_storage):
    section_image_id = "a" * 32
    item_image_id = "b" * 32
    with get_db() as conn:
        conn.execute(
            "UPDATE home_sections SET image_id = %s WHERE slug = 'hero'",
            (section_image_id,),
        )
        item_id = conn.execute(
            "SELECT id FROM home_items WHERE section = 'trust' AND is_published = 1 ORDER BY sort_order LIMIT 1"
        ).fetchone()["id"]
        conn.execute("UPDATE home_items SET image_id = %s WHERE id = %s", (item_image_id, item_id))

    sections = home_service.get_public_home()["sections"]
    hero = next(section for section in sections if section["slug"] == "hero")
    trust = next(section for section in sections if section["slug"] == "trust")
    item = next(item for item in trust["items"] if item["id"] == item_id)

    assert hero["image"] == f"{R2_TEST_PUBLIC_BASE}/products/home-hero_{section_image_id}.webp"
    assert item["image"] == (
        f"{R2_TEST_PUBLIC_BASE}/products/home-item-{item_id}_{item_image_id}.webp"
    )


def test_reorder_sections_validates_submitted_set(db):
    with pytest.raises(HomeReorderError):
        home_service.reorder_sections(["hero", "trust"])


def test_section_slug_and_type_are_immutable(db):
    with pytest.raises(HomeValidationError):
        home_service.update_section_text("hero", {"type": "cards"})
    with pytest.raises(HomeValidationError):
        home_service.update_section_text("hero", {"slug": "new-hero"})


def test_sanitization_escapes_html_on_write(db):
    raw_text = "<script>alert(1)</script><b>Clean</b>"
    updated = home_service.update_section_text("hero", {"body_en": raw_text})
    assert updated["body_en"] == raw_text

    with get_db() as conn:
        stored = conn.execute("SELECT body_en FROM home_sections WHERE slug = 'hero'").fetchone()[
            "body_en"
        ]
    assert "<script>" not in stored
    assert "&lt;script&gt;" in stored
