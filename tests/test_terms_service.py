"""Service and seed tests for admin-managed Terms content."""

import pytest

from app.database import get_db
from app.services import terms_service
from app.services.terms_service import TermsNotFoundError, TermsValidationError


def test_seed_matches_existing_terms_copy_and_public_locale(db):
    en = terms_service.get_public_terms("en")
    assert en["title"] == "Terms & Conditions"
    assert any(section["id"] == "returns" for section in en["sections"])
    returns_en = next(section for section in en["sections"] if section["id"] == "returns")
    assert returns_en["nav"] == "Returns"
    assert returns_en["model_form_lines"]

    bg = terms_service.get_public_terms("bg")
    assert bg["title"] == "Общи условия"
    returns_bg = next(section for section in bg["sections"] if section["id"] == "returns")
    assert returns_bg["nav"] == "Връщане"


def test_admin_update_page_and_section(db):
    page = terms_service.update_page({"title_en": "Legal terms", "title_bg": "Правни условия"})
    assert page["title_en"] == "Legal terms"
    assert page["title_bg"] == "Правни условия"

    section = terms_service.update_section(
        "returns",
        {
            "title_en": "Returns updated",
            "title_bg": "Връщане обновено",
            "body_en": ["First paragraph", "Second paragraph"],
            "body_bg": ["Първи параграф"],
            "model_form_lines_en": ["Line A", "Line B"],
        },
    )
    assert section["title_en"] == "Returns updated"
    assert section["body_en"] == ["First paragraph", "Second paragraph"]
    assert section["model_form_lines_en"] == ["Line A", "Line B"]

    public = terms_service.get_public_terms("bg")
    returns = next(section for section in public["sections"] if section["id"] == "returns")
    assert returns["title"] == "Връщане обновено"
    assert returns["body"] == ["Първи параграф"]


def test_seed_edits_and_deletions_persist(db):
    with get_db() as conn:
        conn.execute("UPDATE terms_page SET title_en = 'Edited terms' WHERE id = 'terms'")
        conn.execute("DELETE FROM terms_sections WHERE slug = 'contact'")

    with get_db() as conn:
        row = conn.execute("SELECT title_en FROM terms_page WHERE id = 'terms'").fetchone()
        assert row["title_en"] == "Edited terms"
        assert (
            conn.execute(
                "SELECT 1 AS present FROM terms_sections WHERE slug = 'contact'"
            ).fetchone()
            is None
        )


def test_invalid_terms_updates_are_rejected(db):
    with pytest.raises(TermsValidationError):
        terms_service.update_page({"title_en": ""})
    with pytest.raises(TermsValidationError):
        terms_service.update_section("returns", {"body_en": []})
    with pytest.raises(TermsNotFoundError):
        terms_service.update_section("missing", {"title_en": "Missing"})
