"""Migration tests for managed product taxonomy (dynamic-categories).

Simulates a legacy pre-taxonomy SQLite file (a products table WITHOUT the
product_type_slug / category_slug columns and free-text `category` values) and
verifies that init_db seeds taxonomy, backfills labels from distinct legacy
category values, records the mapping, defaults product types, leaves category
tiers unset, and is idempotent on re-run.
"""

import sqlite3
from pathlib import Path

import pytest

from app.database import init_db

# A bilingual-but-pre-taxonomy products table: has name_en/category but lacks the
# product_type_slug/category_slug columns, so init_db must rebuild + backfill it.
_LEGACY_PRODUCTS_DDL = """
CREATE TABLE products (
    id          TEXT PRIMARY KEY,
    name_en     TEXT NOT NULL,
    name_bg     TEXT,
    description_en TEXT,
    description_bg TEXT,
    materials   TEXT,
    days_to_craft INTEGER,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    category    TEXT,
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    is_active   INTEGER NOT NULL DEFAULT 1,
    is_featured INTEGER NOT NULL DEFAULT 0,
    translation_stale_bg INTEGER NOT NULL DEFAULT 0,
    translation_stale_en INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _build_legacy_db(path: str, rows: list[tuple[str, str, str | None]]) -> None:
    """Create a legacy products table and insert (id, name_en, category) rows."""
    Path(path).unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_LEGACY_PRODUCTS_DDL)
    conn.executemany(
        "INSERT INTO products (id, name_en, price_cents, category, stock) "
        "VALUES (?, ?, 1000, ?, 5)",
        [(pid, name, cat) for pid, name, cat in rows],
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def legacy_db_path(tmp_path) -> str:
    return str(tmp_path / "legacy.db")


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


class TestSeedsEnsured:
    def test_fresh_db_has_seed_terms(self, tmp_path):
        path = str(tmp_path / "fresh.db")
        init_db(path)
        conn = _connect(path)
        types = {r["slug"] for r in conn.execute("SELECT slug FROM product_types")}
        cats = {r["slug"] for r in conn.execute("SELECT slug FROM product_categories")}
        labels = {r["slug"] for r in conn.execute("SELECT slug FROM product_labels")}
        conn.close()
        assert {"candles", "boxes"}.issubset(types)
        assert {"small", "medium", "premium"}.issubset(cats)
        assert {
            "floral",
            "woody",
            "fresh",
            "gourmand",
            "spicy",
            "citrus",
            "winter",
            "gift",
            "christmas",
        }.issubset(labels)

    def test_migration_marker_recorded(self, tmp_path):
        path = str(tmp_path / "fresh.db")
        init_db(path)
        conn = _connect(path)
        marker = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = 'product_taxonomy_v1'"
        ).fetchone()
        conn.close()
        assert marker is not None


class TestLegacyBackfill:
    def test_legacy_categories_become_labels_and_assignments(self, legacy_db_path):
        _build_legacy_db(
            legacy_db_path,
            [
                ("p-floral", "Floral Candle", "Floral"),
                ("p-woody", "Woody Candle", "Woody"),
                ("p-null", "Plain Candle", None),
            ],
        )
        init_db(legacy_db_path)
        conn = _connect(legacy_db_path)

        # Legacy fragrance families reuse the matching seed labels.
        labels = {r["slug"] for r in conn.execute("SELECT slug FROM product_labels")}
        assert {"floral", "woody"}.issubset(labels)

        assignments = {
            (r["product_id"], r["label_slug"])
            for r in conn.execute("SELECT product_id, label_slug FROM product_label_assignments")
        }
        assert ("p-floral", "floral") in assignments
        assert ("p-woody", "woody") in assignments
        # Null-category product gets no label assignment.
        assert not any(pid == "p-null" for pid, _ in assignments)
        conn.close()

    def test_mapping_recorded(self, legacy_db_path):
        _build_legacy_db(legacy_db_path, [("p1", "One", "Floral"), ("p2", "Two", "Woody")])
        init_db(legacy_db_path)
        conn = _connect(legacy_db_path)
        mapping = {
            r["original_value"]: r["label_slug"]
            for r in conn.execute(
                "SELECT original_value, label_slug FROM taxonomy_category_migration"
            )
        }
        conn.close()
        assert mapping == {"Floral": "floral", "Woody": "woody"}

    def test_products_default_to_candles_and_null_category(self, legacy_db_path):
        _build_legacy_db(legacy_db_path, [("p1", "One", "Floral"), ("p2", "Two", None)])
        init_db(legacy_db_path)
        conn = _connect(legacy_db_path)
        rows = conn.execute(
            "SELECT id, product_type_slug, category_slug FROM products ORDER BY id"
        ).fetchall()
        conn.close()
        for r in rows:
            assert r["product_type_slug"] == "candles"
            assert r["category_slug"] is None

    def test_distinct_values_colliding_slug_get_suffixed(self, legacy_db_path):
        # Two DISTINCT legacy values that slugify to the same base ("sea-breeze").
        _build_legacy_db(
            legacy_db_path,
            [
                ("p-a", "Product A", "Sea Breeze"),
                ("p-b", "Product B", "Sea-Breeze"),
            ],
        )
        init_db(legacy_db_path)
        conn = _connect(legacy_db_path)

        mapping = {
            r["original_value"]: r["label_slug"]
            for r in conn.execute(
                "SELECT original_value, label_slug FROM taxonomy_category_migration"
            )
        }
        # Both originals present, mapped to two DISTINCT slugs, one suffixed -2.
        assert set(mapping.keys()) == {"Sea Breeze", "Sea-Breeze"}
        slugs = set(mapping.values())
        assert slugs == {"sea-breeze", "sea-breeze-2"}

        # Each product is assigned the slug recorded for its exact original value.
        assignments = {
            r["product_id"]: r["label_slug"]
            for r in conn.execute("SELECT product_id, label_slug FROM product_label_assignments")
        }
        assert assignments["p-a"] == mapping["Sea Breeze"]
        assert assignments["p-b"] == mapping["Sea-Breeze"]
        conn.close()


class TestIdempotentReRun:
    def test_rerun_does_not_duplicate_terms_or_assignments(self, legacy_db_path):
        _build_legacy_db(
            legacy_db_path,
            [
                ("p-floral", "Floral Candle", "Floral"),
                ("p-new", "New Scent", "Sea Breeze"),
            ],
        )
        init_db(legacy_db_path)

        conn = _connect(legacy_db_path)
        labels_before = conn.execute("SELECT COUNT(*) AS c FROM product_labels").fetchone()["c"]
        assign_before = conn.execute(
            "SELECT COUNT(*) AS c FROM product_label_assignments"
        ).fetchone()["c"]
        mapping_before = conn.execute(
            "SELECT COUNT(*) AS c FROM taxonomy_category_migration"
        ).fetchone()["c"]
        conn.close()

        # Re-run migration (idempotent, marker-guarded).
        init_db(legacy_db_path)

        conn = _connect(legacy_db_path)
        labels_after = conn.execute("SELECT COUNT(*) AS c FROM product_labels").fetchone()["c"]
        assign_after = conn.execute(
            "SELECT COUNT(*) AS c FROM product_label_assignments"
        ).fetchone()["c"]
        mapping_after = conn.execute(
            "SELECT COUNT(*) AS c FROM taxonomy_category_migration"
        ).fetchone()["c"]
        conn.close()

        assert labels_after == labels_before
        assert assign_after == assign_before
        assert mapping_after == mapping_before
