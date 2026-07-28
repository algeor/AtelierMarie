"""Service tests for the editable atelier story page."""

import pytest

from app.database import get_db, init_db
from app.services import about_service
from app.services.about_service import AboutReorderError, AboutValidationError


@pytest.fixture()
def about_db(tmp_path) -> str:
    path = str(tmp_path / "about.db")
    init_db(path)
    return path


def test_seed_has_expected_sections_and_items_and_is_idempotent(about_db):
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM about_sections").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM about_items").fetchone()[0] == 17

    init_db(about_db)

    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM about_sections").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM about_items").fetchone()[0] == 17


def test_bg_locale_falls_back_to_english(about_db):
    with get_db() as conn:
        conn.execute("UPDATE about_sections SET heading_bg = NULL WHERE slug = 'hero'")

    hero = about_service.get_public_about("bg")["sections"][0]
    assert hero["heading"] == "The Atelier Marie"


def test_public_read_filters_unpublished_sections_and_items(about_db):
    with get_db() as conn:
        conn.execute("UPDATE about_sections SET is_published = 0 WHERE slug = 'philosophy'")
        first_item = conn.execute(
            "SELECT id FROM about_items WHERE section = 'process' ORDER BY sort_order LIMIT 1"
        ).fetchone()[0]
        conn.execute("UPDATE about_items SET is_published = 0 WHERE id = ?", (first_item,))

    sections = about_service.get_public_about()["sections"]
    assert "philosophy" not in [section["slug"] for section in sections]
    process = next(section for section in sections if section["slug"] == "process")
    assert all(item["title"] != "Design" for item in process["items"])


def test_reorder_sections_validates_submitted_set(about_db):
    with pytest.raises(AboutReorderError):
        about_service.reorder_sections(["hero", "story"])


def test_section_slug_and_type_are_immutable(about_db):
    with pytest.raises(AboutValidationError):
        about_service.update_section_text("hero", {"type": "cards"})
    with pytest.raises(AboutValidationError):
        about_service.update_section_text("hero", {"slug": "new-hero"})


def test_sanitization_escapes_html_on_write(about_db):
    updated = about_service.update_section_text(
        "hero", {"body_en": "<script>alert(1)</script><b>Clean</b>"}
    )
    assert "<script>" not in updated["body_en"]
    assert "&lt;script&gt;" in updated["body_en"]
