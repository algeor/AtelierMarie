"""Taxonomy seed invariants under the Postgres migration (Decision 1).

Historically this file simulated a legacy pre-taxonomy *SQLite* database and
asserted that ``init_db`` seeded taxonomy, backfilled ``product_labels`` from
distinct free-text ``category`` values, recorded a mapping, defaulted product
types, and was idempotent on re-run.

Under the Postgres migration the SQLite dialect is gone and ``init_db`` only
opens the psycopg pool: it no longer creates schema, seeds, or backfills. The
schema + structural seed rows are baked into the alembic migration
``20260802_0001`` and carried into every worker DB by the template clone. The
legacy free-text ``category`` backfill code path was deliberately removed, so
the tests that exercised it (``TestLegacyBackfill``, ``TestLegacyValueHygiene``,
``TestExistingLabelAssignmentMigration``, the marker-gated re-run idempotency,
and the ``schema_migrations`` marker) test guarantees that no longer exist and
were retired.

What remains here are the still-valid *seed* invariants against the migrated
Postgres schema. The "deleted seed row is not resurrected on re-init" guarantee
is owned by ``test_taxonomy_review_gaps.TestSeedGatingIsOneShot`` and is not
duplicated here; the orphan-label foreign-key rejection is owned by
``test_taxonomy_review_gaps.TestLabelForeignKey``.
"""


class TestSeedTermsPresent:
    def test_seed_terms_are_present_and_well_formed(self, db):
        types = {r["slug"]: r for r in db.execute("SELECT * FROM product_types").fetchall()}
        cats = {r["slug"]: r for r in db.execute("SELECT * FROM product_categories").fetchall()}
        labels = {r["slug"]: r for r in db.execute("SELECT * FROM product_labels").fetchall()}

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

        # Seed rows carry both locales and are active — the shape downstream
        # taxonomy resolution relies on.
        for row in (*types.values(), *cats.values(), *labels.values()):
            assert row["name_en"]
            assert row["name_bg"]
            assert row["is_active"] == 1

    def test_label_sort_order_is_stable(self, db):
        # Label ordering drives rendered label order (see resolve_products_taxonomy);
        # floral must sort before winter.
        order = {
            r["slug"]: r["sort_order"]
            for r in db.execute("SELECT slug, sort_order FROM product_labels").fetchall()
        }
        assert order["floral"] < order["winter"]
        assert order["floral"] == 0


class TestProductTypeDefault:
    def test_products_default_to_candles_type_and_null_category(self, db):
        # The products table defaults product_type_slug to 'candles' and leaves
        # category_slug unset — the invariant the legacy backfill used to enforce
        # is now a column default in the migration.
        db.execute(
            "INSERT INTO products (id, name_en, price_cents, stock) VALUES (%s, %s, %s, %s)",
            ("p-default", "Plain Candle", 1000, 5),
        )
        row = db.execute(
            "SELECT product_type_slug, category_slug FROM products WHERE id = %s",
            ("p-default",),
        ).fetchone()
        assert row["product_type_slug"] == "candles"
        assert row["category_slug"] is None


class TestNoLegacyBackfill:
    def test_category_migration_table_is_empty(self, db):
        # No legacy free-text backfill runs under Postgres, so the mapping table
        # ships empty. (The table itself still exists for schema compatibility.)
        count = db.execute("SELECT COUNT(*) AS c FROM taxonomy_category_migration").fetchone()["c"]
        assert count == 0
