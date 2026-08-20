"""Service tests for admin-managed SEO landing pages."""

import pytest

from app.services import seo_pages_service
from app.services.seo_pages_service import (
    SeoLandingPageNotFoundError,
    SeoLandingPageValidationError,
)


def test_seed_has_handmade_candles_page(db):
    page = seo_pages_service.get_public_page("handmade-candles", "en")

    assert page["slug"] == "handmade-candles"
    assert page["product_type"] == "candles"
    assert page["path"] == "/handmade-candles"
    assert page["benefits"]
    assert page["faq"]


def test_bg_locale_uses_bg_copy_and_falls_back_to_english(db):
    page = seo_pages_service.update_page(
        "handmade-candles",
        {"title_en": "Edited candles", "title_bg": None},
    )
    assert page["title_en"] == "Edited candles"

    public = seo_pages_service.get_public_page("handmade-candles", "bg")
    assert public["title"] == "Edited candles"
    assert public["path"] == "/rachno-izraboteni-sveshti"


def test_admin_updates_faq_item(db):
    pages = seo_pages_service.list_admin_pages()["pages"]
    item = pages[0]["faq"][0]

    updated = seo_pages_service.update_faq_item(
        "handmade-candles",
        item["id"],
        {"question_en": "Updated question?", "answer_en": "Updated answer."},
    )

    assert updated["question_en"] == "Updated question?"
    public = seo_pages_service.get_public_page("handmade-candles", "en")
    assert public["faq"][0]["question"] == "Updated question?"


def test_invalid_updates_are_rejected(db):
    with pytest.raises(SeoLandingPageValidationError):
        seo_pages_service.update_page("handmade-candles", {"title_en": ""})
    with pytest.raises(SeoLandingPageValidationError):
        seo_pages_service.update_page("handmade-candles", {"benefits_en": []})
    with pytest.raises(SeoLandingPageNotFoundError):
        seo_pages_service.update_page("missing", {"title_en": "Missing"})
