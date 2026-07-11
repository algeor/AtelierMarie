"""Unit tests for the product service layer."""

import sqlite3

import pytest

from app.database import get_db, init_db
from app.services import product_service
from app.services.product_service import DuplicateError, NotFoundError


@pytest.fixture()
def _seeded_db(db_path):
    """Initialize DB and seed with test products."""
    init_db(db_path)
    product_service.create_product(
        {
            "id": "lavender-dream-300ml",
            "name_en": "Lavender Dream",
            "description_en": "A calming lavender candle",
            "price_cents": 3200,
            "category": "luxury-jar",
            "stock": 24,
        }
    )
    product_service.create_product(
        {
            "id": "midnight-amber-300ml",
            "name_en": "Midnight Amber",
            "description_en": "Warm amber and sandalwood",
            "price_cents": 4500,
            "category": "luxury-jar",
            "stock": 12,
        }
    )
    product_service.create_product(
        {
            "id": "vanilla-brulee-200ml",
            "name_en": "Vanilla Crème Brûlée",
            "description_en": "Rich vanilla custard",
            "price_cents": 2800,
            "category": "dessert",
            "stock": 0,
        }
    )


class TestListProducts:
    """Tests for list_products (public, active-only)."""

    def test_returns_active_products(self, _seeded_db):
        products, total = product_service.list_products()
        assert total == 3
        assert len(products) == 3

    def test_filters_by_category(self, _seeded_db):
        products, total = product_service.list_products(category="luxury-jar")
        assert total == 2
        assert all(p["category"] == "luxury-jar" for p in products)

    def test_filters_in_stock_only(self, _seeded_db):
        products, total = product_service.list_products(in_stock=True)
        assert total == 2
        assert all(p["stock"] > 0 for p in products)

    def test_sorts_by_price_asc(self, _seeded_db):
        products, _ = product_service.list_products(sort="price_asc")
        prices = [p["price_cents"] for p in products]
        assert prices == sorted(prices)

    def test_sorts_by_price_desc(self, _seeded_db):
        products, _ = product_service.list_products(sort="price_desc")
        prices = [p["price_cents"] for p in products]
        assert prices == sorted(prices, reverse=True)

    def test_sorts_by_name(self, _seeded_db):
        products, _ = product_service.list_products(sort="name")
        names = [p["name"] for p in products]
        assert names == sorted(names)

    def test_pagination_correct_slice(self, _seeded_db):
        products, total = product_service.list_products(page=1, limit=2)
        assert total == 3
        assert len(products) == 2

        products2, total2 = product_service.list_products(page=2, limit=2)
        assert total2 == 3
        assert len(products2) == 1

    def test_empty_page_beyond_data(self, _seeded_db):
        products, total = product_service.list_products(page=999, limit=20)
        assert total == 3
        assert len(products) == 0

    def test_excludes_inactive_products(self, _seeded_db):
        product_service.deactivate_product("lavender-dream-300ml")
        products, total = product_service.list_products()
        assert total == 2
        ids = [p["id"] for p in products]
        assert "lavender-dream-300ml" not in ids


class TestGetProduct:
    """Tests for get_product (public, active-only)."""

    def test_returns_active_product(self, _seeded_db):
        product = product_service.get_product("lavender-dream-300ml")
        assert product["name"] == "Lavender Dream"
        assert product["price_cents"] == 3200

    def test_raises_not_found_for_missing(self, _seeded_db):
        with pytest.raises(NotFoundError):
            product_service.get_product("no-such-product")

    def test_raises_not_found_for_inactive(self, _seeded_db):
        product_service.deactivate_product("lavender-dream-300ml")
        with pytest.raises(NotFoundError):
            product_service.get_product("lavender-dream-300ml")


class TestCreateProduct:
    """Tests for create_product."""

    def test_creates_new_product(self, db_path):
        init_db(db_path)
        product = product_service.create_product(
            {
                "id": "test-candle-100ml",
                "name_en": "Test Candle",
                "price_cents": 1500,
                "stock": 5,
            }
        )
        assert product["id"] == "test-candle-100ml"
        assert product["name_en"] == "Test Candle"
        assert product["price_cents"] == 1500
        assert product["stock"] == 5
        assert product["is_active"] == 1
        assert product["created_at"] is not None
        assert product["updated_at"] is not None

    def test_raises_duplicate_error(self, _seeded_db):
        with pytest.raises(DuplicateError):
            product_service.create_product(
                {
                    "id": "lavender-dream-300ml",
                    "name_en": "Duplicate",
                    "price_cents": 1000,
                    "stock": 1,
                }
            )


class TestUpsertProduct:
    """Tests for upsert_product."""

    def test_creates_new_product(self, db_path):
        init_db(db_path)
        product = product_service.upsert_product(
            "new-candle",
            {
                "name_en": "New Candle",
                "price_cents": 2000,
                "stock": 10,
            },
        )
        assert product["id"] == "new-candle"
        assert product["name_en"] == "New Candle"

    def test_updates_existing_product(self, _seeded_db):
        product = product_service.upsert_product(
            "lavender-dream-300ml",
            {
                "name_en": "Updated Lavender",
                "price_cents": 3500,
            },
        )
        assert product["name_en"] == "Updated Lavender"
        assert product["price_cents"] == 3500
        # Stock should be preserved
        assert product["stock"] == 24


class TestUpdateProduct:
    """Tests for update_product."""

    def test_partial_update(self, _seeded_db):
        product = product_service.update_product(
            "lavender-dream-300ml",
            {
                "name_en": "Lavender Dream XL",
            },
        )
        assert product["name_en"] == "Lavender Dream XL"
        assert product["price_cents"] == 3200  # Unchanged

    def test_raises_not_found(self, _seeded_db):
        with pytest.raises(NotFoundError):
            product_service.update_product("no-such-product", {"name_en": "X"})

    def test_updates_multiple_fields(self, _seeded_db):
        product = product_service.update_product(
            "lavender-dream-300ml",
            {
                "name_en": "New Name",
                "price_cents": 9999,
                "stock": 100,
            },
        )
        assert product["name_en"] == "New Name"
        assert product["price_cents"] == 9999
        assert product["stock"] == 100


class TestDeactivateProduct:
    """Tests for deactivate_product."""

    def test_deactivates_active_product(self, _seeded_db):
        product = product_service.deactivate_product("lavender-dream-300ml")
        assert product["is_active"] == 0

    def test_idempotent_on_already_inactive(self, _seeded_db):
        product_service.deactivate_product("lavender-dream-300ml")
        # Second call should not raise
        product = product_service.deactivate_product("lavender-dream-300ml")
        assert product["is_active"] == 0

    def test_raises_not_found(self, _seeded_db):
        with pytest.raises(NotFoundError):
            product_service.deactivate_product("no-such-product")


class TestSearchProducts:
    """Tests for search_products (FTS5)."""

    def test_finds_by_name(self, _seeded_db):
        results = product_service.search_products("lavender")
        assert len(results) >= 1
        assert any(r["id"] == "lavender-dream-300ml" for r in results)

    def test_finds_by_description(self, _seeded_db):
        results = product_service.search_products("sandalwood")
        assert len(results) >= 1
        assert any(r["id"] == "midnight-amber-300ml" for r in results)

    def test_excludes_inactive(self, _seeded_db):
        product_service.deactivate_product("lavender-dream-300ml")
        results = product_service.search_products("lavender")
        assert not any(r["id"] == "lavender-dream-300ml" for r in results)

    def test_no_results(self, _seeded_db):
        results = product_service.search_products("xyznonexistent")
        assert results == []

    def test_empty_query_returns_empty(self, _seeded_db):
        results = product_service.search_products("")
        assert results == []


class TestAdminFunctions:
    """Tests for admin-specific service functions."""

    def test_get_product_admin_returns_inactive(self, _seeded_db):
        product_service.deactivate_product("lavender-dream-300ml")
        product = product_service.get_product_admin("lavender-dream-300ml")
        assert product["is_active"] == 0

    def test_get_product_admin_raises_not_found(self, _seeded_db):
        with pytest.raises(NotFoundError):
            product_service.get_product_admin("no-such-product")

    def test_list_products_admin_includes_inactive(self, _seeded_db):
        product_service.deactivate_product("lavender-dream-300ml")
        products, total = product_service.list_products_admin()
        assert total == 3
        ids = [p["id"] for p in products]
        assert "lavender-dream-300ml" in ids


class TestProductConstraints:
    """Tests for database-level constraints."""

    def test_negative_stock_rejected(self, db_path):
        init_db(db_path)
        with pytest.raises(sqlite3.IntegrityError):
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO products "
                    "(id, name_en, price_cents, stock, is_active, created_at, updated_at) "
                    "VALUES ('bad-stock', 'Bad', 1000, -1, 1, "
                    "datetime('now'), datetime('now'))"
                )

    def test_zero_stock_allowed(self, db_path):
        init_db(db_path)
        product = product_service.create_product(
            {
                "id": "zero-stock",
                "name_en": "Zero Stock Candle",
                "price_cents": 1000,
                "stock": 0,
            }
        )
        assert product["stock"] == 0
