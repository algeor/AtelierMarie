"""Public product API taxonomy metadata + faceted filtering (dynamic-categories).

Verifies list/search/detail expose taxonomy display metadata and that the
product_type / category / labels filters work (AND semantics for labels) using
slugs independent of locale. Uses the module-scoped conftest; deleting products
between tests cascades to label assignments, and these tests only reference
active seed terms so shared taxonomy state stays clean.
"""

import pytest


@pytest.fixture()
def _tax_products(app, db_path):
    """Three products spanning both product types, tiers, and labels."""
    from app.services import product_service

    product_service.create_product(
        {
            "id": "winter-candle",
            "name_en": "Winter Candle",
            "description_en": "A cozy winter candle",
            "price_cents": 3000,
            "product_type": "candles",
            "category": "medium",
            "labels": ["winter", "gift"],
            "stock": 10,
        }
    )
    product_service.create_product(
        {
            "id": "small-winter-candle",
            "name_en": "Small Winter Candle",
            "description_en": "A small winter candle",
            "price_cents": 1500,
            "product_type": "candles",
            "category": "small",
            "labels": ["winter"],
            "stock": 10,
        }
    )
    product_service.create_product(
        {
            "id": "gift-box",
            "name_en": "Gift Box",
            "description_en": "A premium gift box",
            "price_cents": 5000,
            "product_type": "boxes",
            "category": "premium",
            "labels": ["gift"],
            "stock": 10,
        }
    )


class TestTaxonomyMetadata:
    @pytest.mark.asyncio
    async def test_detail_includes_metadata(self, client, _tax_products):
        body = (await client.get("/v1/products/winter-candle")).json()
        assert body["product_type"] == "candles"
        assert body["product_type_name"] == "Candles"
        assert body["category"] == "medium"
        assert body["category_name"] == "Medium"
        label_slugs = {lbl["slug"] for lbl in body["labels"]}
        assert label_slugs == {"winter", "gift"}
        assert all("name" in lbl for lbl in body["labels"])

    @pytest.mark.asyncio
    async def test_list_includes_metadata(self, client, _tax_products):
        body = (await client.get("/v1/products")).json()
        box = next(p for p in body["products"] if p["id"] == "gift-box")
        assert box["product_type"] == "boxes"
        assert box["category_name"] == "Premium"
        assert [lbl["slug"] for lbl in box["labels"]] == ["gift"]

    @pytest.mark.asyncio
    async def test_bg_locale_resolves_names(self, client, _tax_products):
        body = (await client.get("/v1/products/winter-candle?locale=bg")).json()
        assert body["product_type_name"] == "Свещи"
        assert body["category_name"] == "Средна"


class TestFacetedFilters:
    @pytest.mark.asyncio
    async def test_filter_by_product_type_candles(self, client, _tax_products):
        body = (await client.get("/v1/products?product_type=candles")).json()
        assert body["total"] == 2
        assert all(p["product_type"] == "candles" for p in body["products"])

    @pytest.mark.asyncio
    async def test_filter_by_product_type_boxes(self, client, _tax_products):
        body = (await client.get("/v1/products?product_type=boxes")).json()
        assert body["total"] == 1
        assert body["products"][0]["id"] == "gift-box"

    @pytest.mark.asyncio
    async def test_filter_by_category(self, client, _tax_products):
        body = (await client.get("/v1/products?category=premium")).json()
        assert body["total"] == 1
        assert body["products"][0]["id"] == "gift-box"

    @pytest.mark.asyncio
    async def test_filter_by_single_label(self, client, _tax_products):
        body = (await client.get("/v1/products?labels=winter")).json()
        ids = {p["id"] for p in body["products"]}
        assert ids == {"winter-candle", "small-winter-candle"}

    @pytest.mark.asyncio
    async def test_filter_by_labels_and_semantics(self, client, _tax_products):
        # Must carry BOTH winter AND gift → only winter-candle.
        body = (await client.get("/v1/products?labels=winter,gift")).json()
        assert body["total"] == 1
        assert body["products"][0]["id"] == "winter-candle"

    @pytest.mark.asyncio
    async def test_filters_combine(self, client, _tax_products):
        body = (
            await client.get("/v1/products?product_type=boxes&category=premium&labels=gift")
        ).json()
        assert body["total"] == 1
        assert body["products"][0]["id"] == "gift-box"

    @pytest.mark.asyncio
    async def test_filtering_slug_based_across_locale(self, client, _tax_products):
        # Filter by the stored slug even when requesting Bulgarian display names.
        body = (await client.get("/v1/products?category=medium&locale=bg")).json()
        assert body["total"] == 1
        assert body["products"][0]["id"] == "winter-candle"
        assert body["products"][0]["category_name"] == "Средна"

    @pytest.mark.asyncio
    async def test_search_with_label_filter(self, client, _tax_products):
        body = (await client.get("/v1/products?q=candle&labels=winter,gift")).json()
        ids = {p["id"] for p in body["products"]}
        assert ids == {"winter-candle"}
