"""Service and seed tests for admin-managed Privacy Policy content."""

import sqlite3

import pytest

from app.database import get_db, init_db
from app.services import privacy_service
from app.services.privacy_service import PrivacyNotFoundError, PrivacyValidationError


@pytest.fixture()
def privacy_db(tmp_path) -> str:
    path = str(tmp_path / "privacy.db")
    init_db(path)
    return path


def test_seed_matches_existing_privacy_copy_and_public_locale(privacy_db):
    en = privacy_service.get_public_privacy("en")
    assert en["title"] == "Privacy Policy"
    assert en["controller_title"] == "Controller details"
    assert any(section["id"] == "rights" for section in en["sections"])
    rights_en = next(section for section in en["sections"] if section["id"] == "rights")
    assert rights_en["nav"] == "Rights"

    bg = privacy_service.get_public_privacy("bg")
    assert bg["title"] == "Политика за поверителност"
    rights_bg = next(section for section in bg["sections"] if section["id"] == "rights")
    assert rights_bg["nav"] == "Права"


def test_admin_update_page_and_section(privacy_db):
    page = privacy_service.update_page(
        {"title_en": "Privacy details", "title_bg": "Данни за поверителност"}
    )
    assert page["title_en"] == "Privacy details"
    assert page["title_bg"] == "Данни за поверителност"

    section = privacy_service.update_section(
        "rights",
        {
            "title_en": "Rights updated",
            "title_bg": "Права обновено",
            "nav_en": "Rights menu",
            "nav_bg": "Права меню",
            "body_en": ["First paragraph", "Second paragraph"],
            "body_bg": ["Първи параграф"],
        },
    )
    assert section["title_en"] == "Rights updated"
    assert section["nav_en"] == "Rights menu"
    assert section["body_en"] == ["First paragraph", "Second paragraph"]

    public = privacy_service.get_public_privacy("bg")
    rights = next(section for section in public["sections"] if section["id"] == "rights")
    assert rights["title"] == "Права обновено"
    assert rights["nav"] == "Права меню"
    assert rights["body"] == ["Първи параграф"]


def test_seed_runs_once_and_does_not_clobber_edits_or_deletions(tmp_path):
    path = str(tmp_path / "seed.db")
    init_db(path)

    with get_db() as conn:
        conn.execute("UPDATE privacy_page SET title_en = 'Edited privacy' WHERE id = 'privacy'")
        conn.execute("DELETE FROM privacy_sections WHERE slug = 'contact'")

    init_db(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    title = conn.execute("SELECT title_en FROM privacy_page WHERE id = 'privacy'").fetchone()[0]
    assert title == "Edited privacy"
    assert conn.execute("SELECT 1 FROM privacy_sections WHERE slug = 'contact'").fetchone() is None
    conn.close()


def test_invalid_privacy_updates_are_rejected(privacy_db):
    with pytest.raises(PrivacyValidationError):
        privacy_service.update_page({"title_en": ""})
    with pytest.raises(PrivacyValidationError):
        privacy_service.update_section("rights", {"body_en": []})
    with pytest.raises(PrivacyNotFoundError):
        privacy_service.update_section("missing", {"title_en": "Missing"})
