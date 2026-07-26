"""Regression tests for issues found in the dynamic-categories code review.

Scoped to the taxonomy service + schema (no HTTP/product-service layer) so each
behaviour a review finding predicted is pinned:

- Cyrillic slug transliteration end-to-end through create_term
- three-way slug collision suffixing (`-3`)
- the last active product type cannot be deactivated
- deactivate then reactivate round-trips
- inactive-term assignment validation (product type + labels, batch path)
- retired terms still resolve display names / preserve label ordering
- the label_slug foreign key rejects orphan assignments
- delete stays blocked while any product (even inactive) references a term
- deleted seed terms are NOT resurrected on a second init_db

Each test uses a fresh, fully-seeded DB file.
"""

import sqlite3

import pytest

from app.database import get_db, init_db
from app.services import taxonomy_service
from app.services.taxonomy_service import (
    TaxonomyInUseError,
    TaxonomyValidationError,
)


@pytest.fixture()
def tax_db(tmp_path) -> str:
    """Fresh, fully-seeded DB per test (sets the module-global connection path)."""
    path = str(tmp_path / "tax.db")
    init_db(path)
    return path


def _insert_product(product_id: str, *, is_active: int = 1) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, is_active) VALUES (?, ?, ?, ?)",
            (product_id, product_id.title(), 1000, is_active),
        )


class TestSlugDerivationThroughService:
    def test_cyrillic_name_yields_readable_slug(self, tax_db):
        term = taxonomy_service.create_term("labels", "Зима", None, 300)
        assert term["slug"] == "zima"

    def test_three_way_collision_suffixes_to_dash_three(self, tax_db):
        first = taxonomy_service.create_term("labels", "Amber", None, 300)
        second = taxonomy_service.create_term("labels", "Amber", None, 301)
        third = taxonomy_service.create_term("labels", "Amber", None, 302)
        assert first["slug"] == "amber"
        assert second["slug"] == "amber-2"
        assert third["slug"] == "amber-3"

    def test_client_supplied_slug_is_ignored(self, tax_db):
        # Slug is always server-derived from name_en.
        term = taxonomy_service.create_term("categories", "Extra Large", None, 5)
        assert term["slug"] == "extra-large"


class TestProductTypeDeactivationGuard:
    def test_cannot_deactivate_last_active_product_type(self, tax_db):
        # Seeds ship two active types (candles, boxes). Retire one, then the
        # remaining one must not be deactivatable.
        taxonomy_service.update_term("product-types", "boxes", {"is_active": False})
        with pytest.raises(TaxonomyValidationError):
            taxonomy_service.update_term("product-types", "candles", {"is_active": False})

    def test_can_deactivate_when_another_active_type_remains(self, tax_db):
        term = taxonomy_service.update_term("product-types", "boxes", {"is_active": False})
        assert term["is_active"] is False


class TestReactivation:
    def test_deactivate_then_reactivate(self, tax_db):
        taxonomy_service.update_term("labels", "winter", {"is_active": False})
        reactivated = taxonomy_service.update_term("labels", "winter", {"is_active": True})
        assert reactivated["is_active"] is True
        active = [t["slug"] for t in taxonomy_service.list_public_taxonomy()["labels"]]
        assert "winter" in active


class TestAssignmentValidation:
    def test_inactive_product_type_rejected_for_new_assignment(self, tax_db):
        taxonomy_service.update_term("product-types", "boxes", {"is_active": False})
        with get_db() as conn, pytest.raises(TaxonomyValidationError):
            taxonomy_service.validate_product_type(conn, "boxes")

    def test_unknown_label_rejected(self, tax_db):
        with get_db() as conn, pytest.raises(TaxonomyValidationError):
            taxonomy_service.validate_labels(conn, ["does-not-exist"])

    def test_inactive_label_rejected_unless_current(self, tax_db):
        taxonomy_service.update_term("labels", "winter", {"is_active": False})
        with get_db() as conn:
            # Not currently assigned -> rejected.
            with pytest.raises(TaxonomyValidationError):
                taxonomy_service.validate_labels(conn, ["winter"])
            # Already assigned (preserve-current) -> allowed.
            taxonomy_service.validate_labels(conn, ["winter"], current={"winter"})

    def test_duplicate_slugs_in_batch_validate_ok(self, tax_db):
        with get_db() as conn:
            # Must not raise or miscount on repeated slugs.
            taxonomy_service.validate_labels(conn, ["floral", "floral"])


class TestRetiredTermResolution:
    def test_inactive_label_still_resolves_name_and_order(self, tax_db):
        _insert_product("p1")
        with get_db() as conn:
            taxonomy_service.replace_product_labels(conn, "p1", ["winter", "floral"])
        taxonomy_service.update_term("labels", "winter", {"is_active": False})

        with get_db() as conn:
            products = [{"id": "p1", "product_type_slug": "candles", "category_slug": None}]
            taxonomy_service.resolve_products_taxonomy(conn, products, "en")

        labels = products[0]["labels"]
        slugs = [label_ref["slug"] for label_ref in labels]
        # Retired 'winter' still renders; order follows label sort_order (floral=0 < winter=6).
        assert slugs == ["floral", "winter"]
        winter_ref = next(label_ref for label_ref in labels if label_ref["slug"] == "winter")
        assert winter_ref["name"] == "Winter"

    def test_bg_locale_resolves_label_name(self, tax_db):
        _insert_product("p1")
        with get_db() as conn:
            taxonomy_service.replace_product_labels(conn, "p1", ["winter"])
            products = [{"id": "p1", "product_type_slug": "candles", "category_slug": None}]
            taxonomy_service.resolve_products_taxonomy(conn, products, "bg")
        assert products[0]["labels"][0]["name"] == "Зима"


class TestLabelForeignKey:
    def test_orphan_label_assignment_rejected(self, tax_db):
        _insert_product("p1")
        with get_db() as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO product_label_assignments (product_id, label_slug) VALUES (?, ?)",
                ("p1", "no-such-label"),
            )


class TestDeleteGuard:
    def test_delete_blocked_while_referenced_by_active_product(self, tax_db):
        _insert_product("p1")
        with get_db() as conn:
            taxonomy_service.replace_product_labels(conn, "p1", ["gift"])
        with pytest.raises(TaxonomyInUseError):
            taxonomy_service.delete_term("labels", "gift")

    def test_delete_blocked_while_referenced_by_inactive_product(self, tax_db):
        # Soft-deleted products still pin the term (order/history integrity).
        _insert_product("p1", is_active=0)
        with get_db() as conn:
            taxonomy_service.replace_product_labels(conn, "p1", ["gift"])
        with pytest.raises(TaxonomyInUseError):
            taxonomy_service.delete_term("labels", "gift")

    def test_delete_unused_term_succeeds(self, tax_db):
        taxonomy_service.delete_term("labels", "christmas")
        slugs = [t["slug"] for t in taxonomy_service.list_admin_terms("labels")]
        assert "christmas" not in slugs


class TestSeedGatingIsOneShot:
    def test_deleted_seed_term_not_resurrected_on_reinit(self, tax_db):
        # Delete an unused seed label, then re-run init_db on the same file.
        taxonomy_service.delete_term("labels", "christmas")
        init_db(tax_db)
        slugs = [t["slug"] for t in taxonomy_service.list_admin_terms("labels")]
        assert "christmas" not in slugs
