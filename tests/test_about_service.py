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


def test_seeded_collection_cards_link_to_label_filters(about_db):
    with get_db() as conn:
        links = [
            row[0]
            for row in conn.execute(
                "SELECT link_href FROM about_items "
                "WHERE section = 'collections' ORDER BY sort_order"
            )
        ]

    assert links == [
        "/products?labels=floral",
        "/products?labels=sculptural",
        "/products?labels=bespoke",
    ]


def test_existing_collection_cards_migrate_from_category_to_label_filters(about_db):
    with get_db() as conn:
        conn.execute("DELETE FROM schema_migrations WHERE name = 'collection_label_filters_v1'")
        conn.execute("DELETE FROM product_labels WHERE slug IN ('sculptural', 'bespoke')")
        conn.execute(
            "UPDATE about_items SET link_href = '/products?category=floral' "
            "WHERE section = 'collections' AND title_en = 'Floral Collection'"
        )
        conn.execute(
            "UPDATE about_items SET link_href = '/products?category=sculptural' "
            "WHERE section = 'collections' AND title_en = 'Sculptural Collection'"
        )
        conn.execute(
            "UPDATE about_items SET link_href = '/products?category=bespoke' "
            "WHERE section = 'collections' AND title_en = 'Bespoke Collection'"
        )

    init_db(about_db)

    with get_db() as conn:
        links = [
            row[0]
            for row in conn.execute(
                "SELECT link_href FROM about_items "
                "WHERE section = 'collections' ORDER BY sort_order"
            )
        ]
        labels = {
            row[0]
            for row in conn.execute(
                "SELECT slug FROM product_labels WHERE slug IN ('floral', 'sculptural', 'bespoke')"
            )
        }

    assert links == [
        "/products?labels=floral",
        "/products?labels=sculptural",
        "/products?labels=bespoke",
    ]
    assert labels == {"floral", "sculptural", "bespoke"}


def test_collection_product_label_migration_assigns_known_catalogue_products(about_db):
    with get_db() as conn:
        conn.execute("DELETE FROM schema_migrations WHERE name = 'collection_product_labels_v1'")
        conn.executemany(
            "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, 1000, 5)",
            [
                ("floral-ball-purple-candle", "Floral ball candle"),
                ("spring-blossom-duo", "Spring blossom duo"),
                ("plain-candle", "Plain candle"),
            ],
        )

    init_db(about_db)

    with get_db() as conn:
        assignments = {
            (row[0], row[1])
            for row in conn.execute("SELECT product_id, label_slug FROM product_label_assignments")
        }

    assert ("floral-ball-purple-candle", "floral") in assignments
    assert ("floral-ball-purple-candle", "sculptural") in assignments
    assert ("spring-blossom-duo", "floral") in assignments
    assert not any(product_id == "plain-candle" for product_id, _ in assignments)
    assert not any(label_slug == "bespoke" for _, label_slug in assignments)


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
    raw_text = "<script>alert(1)</script><b>Clean</b>"
    updated = about_service.update_section_text("hero", {"body_en": raw_text})
    assert updated["body_en"] == raw_text

    with get_db() as conn:
        stored = conn.execute("SELECT body_en FROM about_sections WHERE slug = 'hero'").fetchone()[
            0
        ]
    assert "<script>" not in stored
    assert "&lt;script&gt;" in stored
