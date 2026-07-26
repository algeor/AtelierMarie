"""Unit tests for the taxonomy service layer (dynamic-categories).

Covers public listing, admin CRUD, slug derivation/immutability, delete guards,
assignment validation (including preserve-current-inactive rules), and the
batched display-name resolver.

Each test gets a fresh DB file (`tax_db`) because taxonomy tables persist across
init_db calls (seeds use INSERT OR IGNORE) and the shared module cleanup fixture
does not reset taxonomy state — deactivations would otherwise leak between tests.
"""

import pytest

from app.database import get_db, init_db
from app.services import product_service, taxonomy_service
from app.services.taxonomy_service import (
    TaxonomyInUseError,
    TaxonomyNotFoundError,
    TaxonomyValidationError,
)


@pytest.fixture()
def tax_db(tmp_path) -> str:
    """Fresh, fully-seeded DB per test (sets the module-global connection path)."""
    path = str(tmp_path / "tax.db")
    init_db(path)
    return path


def _deactivate(kind: str, slug: str) -> None:
    """Directly flip is_active=0 on a term (bypasses admin route)."""
    taxonomy_service.update_term(kind, slug, {"is_active": False})


# ===========================================================================
# Public taxonomy listing
# ===========================================================================


class TestPublicTaxonomy:
    def test_returns_seeded_active_terms(self, tax_db):
        tax = taxonomy_service.list_public_taxonomy()
        type_slugs = [t["slug"] for t in tax["product_types"]]
        cat_slugs = [t["slug"] for t in tax["categories"]]
        label_slugs = [t["slug"] for t in tax["labels"]]
        assert type_slugs == ["candles", "boxes"]
        assert cat_slugs == ["small", "medium", "premium"]
        assert "floral" in label_slugs and "christmas" in label_slugs

    def test_ordered_by_sort_order(self, tax_db):
        cats = taxonomy_service.list_public_taxonomy()["categories"]
        orders = [c["sort_order"] for c in cats]
        assert orders == sorted(orders)

    def test_excludes_inactive_terms(self, tax_db):
        _deactivate("labels", "winter")
        label_slugs = [t["slug"] for t in taxonomy_service.list_public_taxonomy()["labels"]]
        assert "winter" not in label_slugs

    def test_locale_bg_uses_bulgarian_name(self, tax_db):
        tax = taxonomy_service.list_public_taxonomy(locale="bg")
        candles = next(t for t in tax["product_types"] if t["slug"] == "candles")
        assert candles["name"] == "Свещи"

    def test_locale_bg_falls_back_to_english_when_null(self, tax_db):
        # Create a term with no BG name, then read in bg locale.
        taxonomy_service.create_term("labels", "Relaxing", None, 200)
        tax = taxonomy_service.list_public_taxonomy(locale="bg")
        relaxing = next(t for t in tax["labels"] if t["slug"] == "relaxing")
        assert relaxing["name"] == "Relaxing"


# ===========================================================================
# Admin CRUD
# ===========================================================================


class TestAdminCRUD:
    def test_create_derives_slug(self, tax_db):
        term = taxonomy_service.create_term("product-types", "Gift Boxes", None, 5)
        assert term["slug"] == "gift-boxes"
        assert term["name_en"] == "Gift Boxes"
        assert term["is_active"] is True
        assert term["product_count"] == 0

    def test_create_slug_collision_suffixed(self, tax_db):
        # "Candles" already seeded as slug "candles".
        term = taxonomy_service.create_term("product-types", "Candles", None, 9)
        assert term["slug"] == "candles-2"

    def test_list_admin_includes_inactive(self, tax_db):
        _deactivate("labels", "winter")
        slugs = {t["slug"] for t in taxonomy_service.list_admin_terms("labels")}
        assert "winter" in slugs

    def test_list_admin_reports_product_count(self, tax_db):
        product_service.create_product(
            {
                "id": "count-candle",
                "name_en": "Count Candle",
                "price_cents": 1000,
                "category": "medium",
                "labels": ["floral"],
                "stock": 1,
            }
        )
        cats = {
            t["slug"]: t["product_count"] for t in taxonomy_service.list_admin_terms("categories")
        }
        labels = {
            t["slug"]: t["product_count"] for t in taxonomy_service.list_admin_terms("labels")
        }
        types = {
            t["slug"]: t["product_count"]
            for t in taxonomy_service.list_admin_terms("product-types")
        }
        assert cats["medium"] == 1
        assert cats["small"] == 0
        assert labels["floral"] == 1
        assert types["candles"] == 1

    def test_rename_keeps_slug(self, tax_db):
        updated = taxonomy_service.update_term("categories", "medium", {"name_en": "Standard"})
        assert updated["slug"] == "medium"
        assert updated["name_en"] == "Standard"

    def test_reorder_changes_sort_order(self, tax_db):
        updated = taxonomy_service.update_term("categories", "small", {"sort_order": 99})
        assert updated["sort_order"] == 99

    def test_deactivate_sets_inactive(self, tax_db):
        updated = taxonomy_service.update_term("labels", "gift", {"is_active": False})
        assert updated["is_active"] is False

    def test_update_missing_raises(self, tax_db):
        with pytest.raises(TaxonomyNotFoundError):
            taxonomy_service.update_term("labels", "no-such-label", {"name_en": "X"})

    def test_get_missing_raises(self, tax_db):
        with pytest.raises(TaxonomyNotFoundError):
            taxonomy_service.get_admin_term("categories", "no-such")


# ===========================================================================
# Delete guards
# ===========================================================================


class TestDeleteGuards:
    def test_delete_unused_term(self, tax_db):
        taxonomy_service.create_term("labels", "Temporary", None, 300)
        taxonomy_service.delete_term("labels", "temporary")
        with pytest.raises(TaxonomyNotFoundError):
            taxonomy_service.get_admin_term("labels", "temporary")

    def test_delete_in_use_label_raises(self, tax_db):
        product_service.create_product(
            {
                "id": "labelled",
                "name_en": "Labelled",
                "price_cents": 1000,
                "labels": ["winter"],
                "stock": 1,
            }
        )
        with pytest.raises(TaxonomyInUseError):
            taxonomy_service.delete_term("labels", "winter")

    def test_delete_in_use_product_type_raises(self, tax_db):
        product_service.create_product(
            {
                "id": "typed",
                "name_en": "Typed",
                "price_cents": 1000,
                "product_type": "candles",
                "stock": 1,
            }
        )
        with pytest.raises(TaxonomyInUseError):
            taxonomy_service.delete_term("product-types", "candles")

    def test_delete_in_use_category_raises(self, tax_db):
        product_service.create_product(
            {
                "id": "categorised",
                "name_en": "Categorised",
                "price_cents": 1000,
                "category": "premium",
                "stock": 1,
            }
        )
        with pytest.raises(TaxonomyInUseError):
            taxonomy_service.delete_term("categories", "premium")

    def test_delete_missing_raises(self, tax_db):
        with pytest.raises(TaxonomyNotFoundError):
            taxonomy_service.delete_term("labels", "no-such")


# ===========================================================================
# Assignment validation
# ===========================================================================


class TestAssignmentValidation:
    def test_valid_create(self, tax_db):
        product = product_service.create_product(
            {
                "id": "valid-candle",
                "name_en": "Valid Candle",
                "price_cents": 2000,
                "product_type": "candles",
                "category": "medium",
                "labels": ["winter", "gift"],
                "stock": 5,
            }
        )
        assert product["product_type"] == "candles"
        assert product["category"] == "medium"
        assert set(product["labels"]) == {"winter", "gift"}

    def test_category_may_be_null(self, tax_db):
        product = product_service.create_product(
            {
                "id": "uncategorised",
                "name_en": "Uncategorised",
                "price_cents": 2000,
                "stock": 5,
            }
        )
        assert product["category"] is None

    def test_unknown_product_type_rejected(self, tax_db):
        with pytest.raises(TaxonomyValidationError):
            product_service.create_product(
                {
                    "id": "bad-type",
                    "name_en": "Bad Type",
                    "price_cents": 2000,
                    "product_type": "not-a-real-type",
                    "stock": 5,
                }
            )

    def test_unknown_category_rejected(self, tax_db):
        with pytest.raises(TaxonomyValidationError):
            product_service.create_product(
                {
                    "id": "bad-cat",
                    "name_en": "Bad Cat",
                    "price_cents": 2000,
                    "category": "luxury-jar",
                    "stock": 5,
                }
            )

    def test_unknown_label_rejected(self, tax_db):
        with pytest.raises(TaxonomyValidationError):
            product_service.create_product(
                {
                    "id": "bad-label",
                    "name_en": "Bad Label",
                    "price_cents": 2000,
                    "labels": ["winter", "unknown-label"],
                    "stock": 5,
                }
            )

    def test_inactive_category_assignment_rejected(self, tax_db):
        _deactivate("categories", "premium")
        with pytest.raises(TaxonomyValidationError):
            product_service.create_product(
                {
                    "id": "inactive-cat",
                    "name_en": "Inactive Cat",
                    "price_cents": 2000,
                    "category": "premium",
                    "stock": 5,
                }
            )

    def test_inactive_label_assignment_rejected(self, tax_db):
        _deactivate("labels", "winter")
        with pytest.raises(TaxonomyValidationError):
            product_service.create_product(
                {
                    "id": "inactive-label",
                    "name_en": "Inactive Label",
                    "price_cents": 2000,
                    "labels": ["winter"],
                    "stock": 5,
                }
            )


class TestUpdatePreservesInactive:
    def _make_product_with_inactive_terms(self):
        product_service.create_product(
            {
                "id": "keeper",
                "name_en": "Keeper",
                "price_cents": 2000,
                "category": "premium",
                "labels": ["winter"],
                "stock": 5,
            }
        )
        _deactivate("categories", "premium")
        _deactivate("labels", "winter")

    def test_unrelated_update_preserves_inactive(self, tax_db):
        self._make_product_with_inactive_terms()
        product = product_service.update_product("keeper", {"price_cents": 2500})
        assert product["price_cents"] == 2500
        assert product["category"] == "premium"
        assert product["labels"] == ["winter"]

    def test_resubmitting_same_inactive_set_allowed(self, tax_db):
        self._make_product_with_inactive_terms()
        product = product_service.update_product(
            "keeper",
            {"category": "premium", "labels": ["winter"]},
        )
        assert product["category"] == "premium"
        assert product["labels"] == ["winter"]

    def test_reassign_to_different_inactive_category_rejected(self, tax_db):
        product_service.create_product(
            {
                "id": "reassign",
                "name_en": "Reassign",
                "price_cents": 2000,
                "category": "medium",
                "stock": 5,
            }
        )
        _deactivate("categories", "premium")
        with pytest.raises(TaxonomyValidationError):
            product_service.update_product("reassign", {"category": "premium"})

    def test_reassign_to_different_inactive_label_rejected(self, tax_db):
        product_service.create_product(
            {
                "id": "reassign-label",
                "name_en": "Reassign Label",
                "price_cents": 2000,
                "labels": ["floral"],
                "stock": 5,
            }
        )
        _deactivate("labels", "winter")
        with pytest.raises(TaxonomyValidationError):
            product_service.update_product("reassign-label", {"labels": ["winter"]})

    def test_reassign_to_different_inactive_product_type_rejected(self, tax_db):
        product_service.create_product(
            {
                "id": "reassign-type",
                "name_en": "Reassign Type",
                "price_cents": 2000,
                "product_type": "candles",
                "stock": 5,
            }
        )
        _deactivate("product-types", "boxes")
        with pytest.raises(TaxonomyValidationError):
            product_service.update_product("reassign-type", {"product_type": "boxes"})

    def test_category_can_be_set_null(self, tax_db):
        product_service.create_product(
            {
                "id": "clear-cat",
                "name_en": "Clear Cat",
                "price_cents": 2000,
                "category": "medium",
                "stock": 5,
            }
        )
        product = product_service.update_product("clear-cat", {"category": None})
        assert product["category"] is None


# ===========================================================================
# Display-name resolution (inactive referenced terms still render)
# ===========================================================================


class TestDisplayResolution:
    def test_inactive_referenced_terms_still_resolve(self, tax_db):
        product_service.create_product(
            {
                "id": "render-me",
                "name_en": "Render Me",
                "price_cents": 2000,
                "category": "premium",
                "labels": ["winter"],
                "stock": 5,
            }
        )
        _deactivate("categories", "premium")
        _deactivate("labels", "winter")
        product = product_service.get_product("render-me")
        assert product["category"] == "premium"
        assert product["category_name"] == "Premium"
        assert product["labels"] == [{"slug": "winter", "name": "Winter"}]

    def test_missing_taxonomy_row_falls_back_to_slug(self, tax_db):
        # Insert a product directly referencing a category slug that has no row.
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, product_type_slug, "
                "category_slug, stock, is_active, created_at, updated_at) VALUES "
                "('orphan', 'Orphan', 1000, 'candles', 'ghost-cat', 1, 1, "
                "datetime('now'), datetime('now'))"
            )
        product = product_service.get_product("orphan")
        assert product["category"] == "ghost-cat"
        assert product["category_name"] == "ghost-cat"
