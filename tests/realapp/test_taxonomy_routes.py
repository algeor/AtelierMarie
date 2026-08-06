"""Integration tests for taxonomy endpoints (dynamic-categories).

Uses the realapp fixtures (function-scoped fresh DB + real middleware) so admin
CRUD mutations to the shared taxonomy tables stay isolated per test.

Under the Postgres template-clone model the seed taxonomy tables are NOT
truncated by the root ``_clean_tables`` autouse (they carry the migration-baked
seed rows), so admin CRUD in one test would otherwise leak into the next. The
``_restore_taxonomy_seeds`` autouse fixture below snapshots the seed taxonomy
tables around each test and restores them, preserving the per-test isolation the
suite was written against.
"""

import pytest

_SEED_TAXONOMY_TABLES = ("product_types", "product_categories", "product_labels")


@pytest.fixture(autouse=True)
def _restore_taxonomy_seeds(app):
    """Snapshot and restore the seed taxonomy tables around each test.

    The migration bakes the seed terms into every worker DB and the root
    truncation deliberately skips these tables, so admin mutations (create /
    rename / deactivate / delete) persist across tests. Capture each seed table's
    rows before the test and rewrite them afterwards so every test starts from the
    baked seed state.
    """
    from app.database import get_db

    with get_db() as conn:
        snapshots = {
            table: [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]  # noqa: S608
            for table in _SEED_TAXONOMY_TABLES
        }
    yield
    with get_db() as conn:
        # Clear rows that FK-reference the seed tables before rewriting them
        # (both are volatile and get truncated before the next test anyway).
        conn.execute("DELETE FROM product_label_assignments")
        conn.execute("DELETE FROM products")
        for table in _SEED_TAXONOMY_TABLES:
            rows = snapshots[table]
            conn.execute(f"DELETE FROM {table}")  # noqa: S608
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ", ".join("%s" for _ in columns)
            col_list = ", ".join(columns)
            with conn.cursor() as cur:
                cur.executemany(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",  # noqa: S608
                    [tuple(row[c] for c in columns) for row in rows],
                )


async def _create_product(admin_client, **overrides):
    payload = {
        "id": "tax-product",
        "name_en": "Tax Product",
        "price_cents": 2000,
        "stock": 5,
    }
    payload.update(overrides)
    resp = await admin_client.post("/v1/admin/products", json=payload)
    return resp


class TestPublicTaxonomy:
    @pytest.mark.asyncio
    async def test_returns_active_terms_ordered(self, client):
        resp = await client.get("/v1/taxonomy")
        assert resp.status_code == 200
        body = resp.json()
        assert [t["slug"] for t in body["product_types"]] == ["candles", "boxes"]
        assert [t["slug"] for t in body["categories"]] == ["small", "medium", "premium"]
        # Ordered by sort_order.
        orders = [t["sort_order"] for t in body["labels"]]
        assert orders == sorted(orders)

    @pytest.mark.asyncio
    async def test_bg_locale_with_fallback(self, admin_client, client):
        # Seed a label with no BG name.
        await admin_client.post("/v1/admin/taxonomy/labels", json={"name_en": "Relaxing"})
        resp = await client.get("/v1/taxonomy?locale=bg")
        body = resp.json()
        candles = next(t for t in body["product_types"] if t["slug"] == "candles")
        relaxing = next(t for t in body["labels"] if t["slug"] == "relaxing")
        assert candles["name"] == "Свещи"  # localized
        assert relaxing["name"] == "Relaxing"  # fallback to name_en

    @pytest.mark.asyncio
    async def test_inactive_excluded(self, admin_client, client):
        await admin_client.patch("/v1/admin/taxonomy/labels/winter", json={"is_active": False})
        resp = await client.get("/v1/taxonomy")
        label_slugs = [t["slug"] for t in resp.json()["labels"]]
        assert "winter" not in label_slugs


class TestAdminTaxonomyCRUD:
    @pytest.mark.asyncio
    async def test_create_derives_slug(self, admin_client):
        resp = await admin_client.post(
            "/v1/admin/taxonomy/product-types", json={"name_en": "Gift Boxes"}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["slug"] == "gift-boxes"
        assert body["is_active"] is True
        assert body["product_count"] == 0

    @pytest.mark.asyncio
    async def test_rename_keeps_slug(self, admin_client):
        resp = await admin_client.patch(
            "/v1/admin/taxonomy/categories/medium", json={"name_en": "Standard"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == "medium"
        assert body["name_en"] == "Standard"

    @pytest.mark.asyncio
    async def test_reorder(self, admin_client):
        resp = await admin_client.patch(
            "/v1/admin/taxonomy/categories/small", json={"sort_order": 42}
        )
        assert resp.json()["sort_order"] == 42

    @pytest.mark.asyncio
    async def test_list_includes_inactive_and_counts(self, admin_client):
        await _create_product(admin_client, labels=["winter"])
        await admin_client.patch("/v1/admin/taxonomy/labels/winter", json={"is_active": False})
        resp = await admin_client.get("/v1/admin/taxonomy/labels")
        assert resp.status_code == 200
        terms = {t["slug"]: t for t in resp.json()}
        assert "winter" in terms  # inactive still listed
        assert terms["winter"]["is_active"] is False
        assert terms["winter"]["product_count"] == 1

    @pytest.mark.asyncio
    async def test_deactivate_hides_from_public_but_product_displays(self, admin_client, client):
        await _create_product(admin_client, labels=["winter"])
        await admin_client.patch("/v1/admin/taxonomy/labels/winter", json={"is_active": False})

        # Hidden from public taxonomy.
        pub = await client.get("/v1/taxonomy")
        assert "winter" not in [t["slug"] for t in pub.json()["labels"]]

        # Referencing product still displays the (inactive) label with its name.
        detail = await client.get("/v1/products/tax-product")
        labels = detail.json()["labels"]
        assert {"slug": "winter", "name": "Winter"} in labels

    @pytest.mark.asyncio
    async def test_non_admin_rejected(self, client):
        assert (await client.get("/v1/admin/taxonomy/labels")).status_code == 401
        assert (
            await client.post("/v1/admin/taxonomy/labels", json={"name_en": "X"})
        ).status_code == 401
        assert (
            await client.patch("/v1/admin/taxonomy/labels/winter", json={"name_en": "X"})
        ).status_code == 401
        assert (await client.delete("/v1/admin/taxonomy/labels/winter")).status_code == 401


class TestAdminTaxonomyDelete:
    @pytest.mark.asyncio
    async def test_delete_unused_returns_204(self, admin_client):
        await admin_client.post("/v1/admin/taxonomy/labels", json={"name_en": "Temporary"})
        resp = await admin_client.delete("/v1/admin/taxonomy/labels/temporary")
        assert resp.status_code == 204
        # Gone from admin list.
        listing = await admin_client.get("/v1/admin/taxonomy/labels")
        assert "temporary" not in [t["slug"] for t in listing.json()]

    @pytest.mark.asyncio
    async def test_delete_in_use_label_returns_409(self, admin_client):
        await _create_product(admin_client, labels=["winter"])
        resp = await admin_client.delete("/v1/admin/taxonomy/labels/winter")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "TAXONOMY_IN_USE"

    @pytest.mark.asyncio
    async def test_delete_in_use_product_type_returns_409(self, admin_client):
        await _create_product(admin_client, product_type="candles")
        resp = await admin_client.delete("/v1/admin/taxonomy/product-types/candles")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_missing_returns_404(self, admin_client):
        resp = await admin_client.delete("/v1/admin/taxonomy/labels/no-such")
        assert resp.status_code == 404


class TestProductTaxonomyValidationViaAPI:
    @pytest.mark.asyncio
    async def test_create_valid_taxonomy(self, admin_client):
        resp = await _create_product(
            admin_client,
            product_type="candles",
            category="medium",
            labels=["winter", "gift"],
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["product_type"] == "candles"
        assert body["category"] == "medium"
        assert set(body["labels"]) == {"winter", "gift"}

    @pytest.mark.asyncio
    async def test_unknown_product_type_returns_422(self, admin_client):
        resp = await _create_product(admin_client, product_type="not-real")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_TAXONOMY"

    @pytest.mark.asyncio
    async def test_unknown_label_returns_422(self, admin_client):
        resp = await _create_product(admin_client, labels=["winter", "nope"])
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_inactive_category_returns_422(self, admin_client):
        await admin_client.patch("/v1/admin/taxonomy/categories/premium", json={"is_active": False})
        resp = await _create_product(admin_client, category="premium")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reassign_to_different_inactive_term_returns_422(self, admin_client):
        await _create_product(admin_client, category="medium")
        await admin_client.patch("/v1/admin/taxonomy/categories/premium", json={"is_active": False})
        resp = await admin_client.patch(
            "/v1/admin/products/tax-product", json={"category": "premium"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_update_preserves_current_inactive(self, admin_client):
        await _create_product(admin_client, category="premium", labels=["winter"])
        await admin_client.patch("/v1/admin/taxonomy/categories/premium", json={"is_active": False})
        await admin_client.patch("/v1/admin/taxonomy/labels/winter", json={"is_active": False})
        # Update an unrelated field — inactive assignments preserved.
        resp = await admin_client.patch(
            "/v1/admin/products/tax-product", json={"price_cents": 2500}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["category"] == "premium"
        assert body["labels"] == ["winter"]


async def _import_csv(admin_client, csv_content: str):
    return await admin_client.post(
        "/v1/admin/products/import",
        files={"file": ("products.csv", csv_content, "text/csv")},
    )


class TestCSVImportTaxonomy:
    @pytest.mark.asyncio
    async def test_row_with_active_taxonomy_imports(self, admin_client):
        # labels is comma-separated, so quote it to keep it in one CSV column.
        csv_content = (
            "id,name_en,price_cents,stock,product_type,category,labels\n"
            'csv-tax-1,CSV Tax One,2000,10,candles,small,"winter,gift"\n'
        )
        resp = await _import_csv(admin_client, csv_content)
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] == 1
        assert body["errors"] == []

        detail = (await admin_client.get("/v1/admin/products/csv-tax-1")).json()
        assert detail["product_type"] == "candles"
        assert detail["category"] == "small"
        assert set(detail["labels"]) == {"winter", "gift"}

    @pytest.mark.asyncio
    async def test_row_with_unknown_product_type_skipped(self, admin_client):
        csv_content = (
            "id,name_en,price_cents,stock,product_type\ncsv-bad-type,Bad Type,2000,10,new-family\n"
        )
        resp = await _import_csv(admin_client, csv_content)
        body = resp.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1
        assert body["errors"][0]["row"] == 2
        # Product not created.
        assert (await admin_client.get("/v1/admin/products/csv-bad-type")).status_code == 404

    @pytest.mark.asyncio
    async def test_row_with_unknown_label_skipped_and_not_created(self, admin_client):
        csv_content = (
            "id,name_en,price_cents,stock,labels\ncsv-bad-label,Bad Label,2000,10,brand-new-label\n"
        )
        resp = await _import_csv(admin_client, csv_content)
        body = resp.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1

        # CSV import must NOT auto-create the label.
        labels = (await admin_client.get("/v1/admin/taxonomy/labels")).json()
        assert "brand-new-label" not in [t["slug"] for t in labels]

    @pytest.mark.asyncio
    async def test_row_with_inactive_category_skipped(self, admin_client):
        await admin_client.patch("/v1/admin/taxonomy/categories/premium", json={"is_active": False})
        csv_content = (
            "id,name_en,price_cents,stock,category\ncsv-inactive-cat,Inactive Cat,2000,10,premium\n"
        )
        resp = await _import_csv(admin_client, csv_content)
        body = resp.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1
        assert (await admin_client.get("/v1/admin/products/csv-inactive-cat")).status_code == 404
