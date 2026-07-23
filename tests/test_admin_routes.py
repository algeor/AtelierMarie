"""Integration tests for admin product endpoints."""

import pytest


@pytest.fixture()
def _products(db_path, app):
    """Seed test products."""
    from app.services import product_service

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
            "id": "inactive-candle",
            "name_en": "Inactive Candle",
            "description_en": "This one is deactivated",
            "price_cents": 1000,
            "category": "seasonal",
            "stock": 5,
            "is_active": False,
        }
    )


class TestAdminAuth:
    """Tests for admin authentication dependency."""

    @pytest.mark.asyncio
    async def test_rejects_no_credentials(self, app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_invalid_key(self, app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer wrong-key"
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_empty_key(self, app, monkeypatch):
        """Empty API key config denies all access."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "admin_api_key", "")

        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer "
            response = await c.get("/v1/admin/products")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_valid_key(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products")
        assert response.status_code == 200


class TestAdminCreateProduct:
    """Tests for POST /v1/admin/products."""

    @pytest.mark.asyncio
    async def test_creates_product(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "new-candle-100ml",
                "name_en": "New Candle",
                "price_cents": 2000,
                "stock": 10,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["id"] == "new-candle-100ml"
        assert body["name_en"] == "New Candle"
        assert body["price_cents"] == 2000

    @pytest.mark.asyncio
    async def test_create_defaults_weight_to_300(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "no-weight-candle",
                "name_en": "No Weight",
                "price_cents": 2000,
                "stock": 5,
            },
        )
        assert response.status_code == 201
        assert response.json()["weight_grams"] == 300

    @pytest.mark.asyncio
    async def test_create_persists_explicit_weight(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "heavy-candle",
                "name_en": "Heavy",
                "price_cents": 2000,
                "stock": 5,
                "weight_grams": 550,
            },
        )
        assert response.status_code == 201
        assert response.json()["weight_grams"] == 550

    @pytest.mark.asyncio
    async def test_returns_409_for_duplicate(self, admin_client, _products):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "lavender-dream-300ml",
                "name_en": "Duplicate",
                "price_cents": 1000,
                "stock": 1,
            },
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "DUPLICATE"

    @pytest.mark.asyncio
    async def test_returns_422_for_invalid_data(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "x",
                "name_en": "",
                "price_cents": -1,
                "stock": 0,
            },
        )
        assert response.status_code == 422


class TestAdminListProducts:
    """Tests for GET /v1/admin/products."""

    @pytest.mark.asyncio
    async def test_lists_all_products_including_inactive(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        ids = [p["id"] for p in body["products"]]
        assert "inactive-candle" in ids

    @pytest.mark.asyncio
    async def test_pagination(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products?page=1&limit=1")
        body = response.json()
        assert body["total"] == 2
        assert len(body["products"]) == 1


class TestAdminGetProduct:
    """Tests for GET /v1/admin/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_returns_active_product(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/lavender-dream-300ml")
        assert response.status_code == 200
        assert response.json()["name_en"] == "Lavender Dream"

    @pytest.mark.asyncio
    async def test_returns_inactive_product(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/inactive-candle")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/no-such-product")
        assert response.status_code == 404


class TestAdminUpdateProduct:
    """Tests for PUT /v1/admin/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_partial_update(self, admin_client, _products):
        response = await admin_client.put(
            "/v1/admin/products/lavender-dream-300ml",
            json={"name_en": "Lavender Dream XL"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name_en"] == "Lavender Dream XL"
        assert body["price_cents"] == 3200  # Unchanged

    @pytest.mark.asyncio
    async def test_update_weight(self, admin_client, _products):
        response = await admin_client.put(
            "/v1/admin/products/lavender-dream-300ml",
            json={"weight_grams": 420},
        )
        assert response.status_code == 200
        assert response.json()["weight_grams"] == 420

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, admin_client, _products):
        response = await admin_client.put(
            "/v1/admin/products/no-such-product",
            json={"name_en": "X"},
        )
        assert response.status_code == 404


class TestAdminDeleteProduct:
    """Tests for DELETE /v1/admin/products/{product_id}."""

    @pytest.mark.asyncio
    async def test_soft_deletes_product(self, admin_client, _products):
        response = await admin_client.delete("/v1/admin/products/lavender-dream-300ml")
        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self, admin_client, _products):
        response = await admin_client.delete("/v1/admin/products/no-such-product")
        assert response.status_code == 404


class TestAdminCSVImport:
    """Tests for POST /v1/admin/products/import."""

    @pytest.mark.asyncio
    async def test_imports_new_products(self, admin_client):
        csv_content = (
            "id,name,price_cents,stock,category\n"
            "csv-candle-1,CSV Candle One,2000,10,dessert\n"
            "csv-candle-2,CSV Candle Two,3000,5,luxury-jar\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["created"] == 2
        assert body["updated"] == 0
        assert body["errors"] == []

    @pytest.mark.asyncio
    async def test_upsert_existing_products(self, admin_client, _products):
        csv_content = (
            "id,name,price_cents,stock\n"
            "lavender-dream-300ml,Updated Lavender,3500,30\n"
            "new-product-csv,Brand New,1500,20\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1
        assert body["updated"] == 1
        assert body["errors"] == []

    @pytest.mark.asyncio
    async def test_validation_errors_skip_rows(self, admin_client):
        csv_content = (
            "id,name,price_cents,stock\n"
            "good-candle,Good Candle,2000,10\n"
            ",Missing ID,2000,10\n"
            "bad-price,Bad Price,-100,10\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1
        assert len(body["errors"]) == 2
        # Check row numbers
        error_rows = [e["row"] for e in body["errors"]]
        assert 3 in error_rows
        assert 4 in error_rows

    @pytest.mark.asyncio
    async def test_missing_required_columns(self, admin_client):
        csv_content = "name,stock\nSome Product,10\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "INVALID_CSV"
        assert "id" in body["error"]["message"]
        assert "price_cents" in body["error"]["message"]

    @pytest.mark.asyncio
    async def test_empty_csv_headers_only(self, admin_client):
        csv_content = "id,name,price_cents\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["created"] == 0
        assert body["updated"] == 0
        assert body["errors"] == []

    @pytest.mark.asyncio
    async def test_imports_extended_optional_columns(self, admin_client):
        csv_content = (
            "id,name_en,price_cents,stock,weight_grams,is_active,is_featured,"
            "materials,days_to_craft\n"
            "ext-candle,Extended Candle,2000,10,550,false,yes,Soy wax,4\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["created"] == 1
        # Verify the values were applied
        detail = await admin_client.get("/v1/admin/products/ext-candle")
        body = detail.json()
        assert body["weight_grams"] == 550
        assert body["is_active"] is False
        assert body["is_featured"] is True
        assert body["materials"] == "Soy wax"
        assert body["days_to_craft"] == 4

    @pytest.mark.asyncio
    async def test_import_without_weight_defaults_new_to_300(self, admin_client):
        csv_content = "id,name_en,price_cents,stock\nplain-candle,Plain,2000,5\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.json()["created"] == 1
        detail = await admin_client.get("/v1/admin/products/plain-candle")
        assert detail.json()["weight_grams"] == 300

    @pytest.mark.asyncio
    async def test_import_without_weight_preserves_existing(self, admin_client):
        # Create with an explicit non-default weight
        await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "keep-weight",
                "name_en": "Keep Weight",
                "price_cents": 2000,
                "stock": 5,
                "weight_grams": 700,
            },
        )
        # Upsert via CSV without a weight_grams column
        csv_content = "id,name_en,price_cents,stock\nkeep-weight,Keep Weight,2500,8\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.json()["updated"] == 1
        detail = await admin_client.get("/v1/admin/products/keep-weight")
        assert detail.json()["weight_grams"] == 700  # unchanged

    @pytest.mark.asyncio
    async def test_import_invalid_weight_and_bool_skip_rows(self, admin_client):
        csv_content = (
            "id,name_en,price_cents,stock,weight_grams,is_active\n"
            "bad-weight,Bad Weight,2000,10,abc,true\n"
            "bad-bool,Bad Bool,2000,10,300,maybe\n"
            "zero-weight,Zero Weight,2000,10,0,true\n"
            "good-row,Good Row,2000,10,300,true\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1
        error_rows = [e["row"] for e in body["errors"]]
        assert 2 in error_rows  # abc weight
        assert 3 in error_rows  # maybe bool
        assert 4 in error_rows  # zero weight (< 1)

    @pytest.mark.asyncio
    async def test_import_days_to_craft_over_max_rejected(self, admin_client):
        """CSV days_to_craft bypasses Pydantic but must still honor le=365."""
        csv_content = (
            "id,name_en,price_cents,stock,days_to_craft\n"
            "too-slow,Too Slow,2000,5,99999\n"
            "negative-days,Negative,2000,5,-1\n"
            "not-int,Not Int,2000,5,abc\n"
            "ok-days,OK Days,2000,5,30\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1
        error_rows = [e["row"] for e in body["errors"]]
        assert 2 in error_rows  # > 365
        assert 3 in error_rows  # negative
        assert 4 in error_rows  # non-int

    @pytest.mark.asyncio
    async def test_import_materials_too_long_rejected(self, admin_client):
        """CSV materials must honor the model's max_length=1000."""
        long_materials = "x" * 1001
        csv_content = (
            f"id,name_en,price_cents,materials\nlong-mat,Long Materials,2000,{long_materials}\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 0
        assert len(body["errors"]) == 1
        assert "materials" in body["errors"][0]["message"]

    @pytest.mark.asyncio
    async def test_import_invalid_id_slug_rejected(self, admin_client):
        """CSV product id must match the slug pattern the API enforces."""
        csv_content = "id,name_en,price_cents\nBad ID!,Bad Slug,2000\ngood-slug-1,Good Slug,2000\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        body = response.json()
        assert body["created"] == 1  # only the good slug
        assert 2 in [e["row"] for e in body["errors"]]

    @pytest.mark.asyncio
    async def test_import_weight_overwrites_existing(self, admin_client):
        """A CSV weight_grams column overwrites an existing product's weight."""
        await admin_client.post(
            "/v1/admin/products",
            json={
                "id": "overwrite-weight",
                "name_en": "Overwrite",
                "price_cents": 2000,
                "stock": 5,
                "weight_grams": 700,
            },
        )
        csv_content = "id,name_en,price_cents,weight_grams\noverwrite-weight,Overwrite,2000,250\n"
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.json()["updated"] == 1
        detail = await admin_client.get("/v1/admin/products/overwrite-weight")
        assert detail.json()["weight_grams"] == 250

    @pytest.mark.asyncio
    async def test_import_bool_case_insensitive_variants(self, admin_client):
        """is_active/is_featured accept true/false/1/0/yes/no case-insensitively."""
        csv_content = (
            "id,name_en,price_cents,is_active,is_featured\n"
            "b-upper,Upper,2000,TRUE,NO\n"
            "b-numeric,Numeric,2000,0,1\n"
        )
        response = await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        assert response.json()["created"] == 2
        upper = (await admin_client.get("/v1/admin/products/b-upper")).json()
        assert upper["is_active"] is True and upper["is_featured"] is False
        numeric = (await admin_client.get("/v1/admin/products/b-numeric")).json()
        assert numeric["is_active"] is False and numeric["is_featured"] is True

    @pytest.mark.asyncio
    async def test_import_csv_created_inactive_hidden_from_public(self, client, admin_client):
        """A CSV-created inactive product is not visible via the public endpoint."""
        csv_content = "id,name_en,price_cents,is_active\nhidden-candle,Hidden,2000,false\n"
        await admin_client.post(
            "/v1/admin/products/import",
            files={"file": ("products.csv", csv_content, "text/csv")},
        )
        public = await client.get("/v1/products/hidden-candle")
        assert public.status_code == 404


class TestAdminLowStockProducts:
    """Tests for GET /v1/admin/products/low-stock."""

    @pytest.mark.asyncio
    async def test_rejects_no_token(self, app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/v1/admin/products/low-stock")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_invalid_key(self, app):
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer wrong-key"
            response = await c.get("/v1/admin/products/low-stock")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_valid_key(self, admin_client, _products):
        response = await admin_client.get("/v1/admin/products/low-stock")
        assert response.status_code == 200
