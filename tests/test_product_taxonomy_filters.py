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
    async def test_filter_by_repeated_label_parameters(self, client, _tax_products):
        body = (await client.get("/v1/products?label=winter&label=gift")).json()
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

    @pytest.mark.asyncio
    async def test_repeated_identical_label_dedupes_in_filter(self, client, _tax_products):
        # `?labels=winter,winter` must behave like a single `winter` (the AND
        # HAVING COUNT(DISTINCT)=? equality would otherwise never match).
        one = (await client.get("/v1/products?labels=winter")).json()
        dup = (await client.get("/v1/products?labels=winter,winter")).json()
        assert dup["total"] == one["total"] == 2


class TestLabelFilterParsing:
    """Unit tests for the public label-filter parser (cap + de-dup)."""

    def test_cap_at_50_distinct_slugs(self):
        from app.routes.products import _MAX_LABEL_FILTERS, _parse_label_filters

        many = ",".join(f"l{i}" for i in range(60))
        parsed = _parse_label_filters(many, None)
        assert parsed is not None
        assert len(parsed) == _MAX_LABEL_FILTERS == 50

    def test_merges_comma_and_repeated_params_with_dedupe(self):
        from app.routes.products import _parse_label_filters

        parsed = _parse_label_filters("winter,gift", ["gift", "floral"])
        assert parsed == ["winter", "gift", "floral"]

    def test_no_labels_returns_none(self):
        from app.routes.products import _parse_label_filters

        assert _parse_label_filters(None, None) is None
        assert _parse_label_filters("", []) is None


class TestLabelFilterPagination:
    """The count query must agree with the paged query under an AND label filter."""

    @pytest.fixture()
    def _many_labeled(self, app, db_path):
        from app.services import product_service

        for i in range(5):
            product_service.create_product(
                {
                    "id": f"lp-{i}",
                    "name_en": f"Labeled {i}",
                    "price_cents": 1000 + i,
                    "product_type": "candles",
                    "labels": ["winter", "gift"],
                    "stock": 5,
                }
            )

    @pytest.mark.asyncio
    async def test_total_counts_all_matches_across_pages(self, client, _many_labeled):
        page2 = (await client.get("/v1/products?labels=winter,gift&limit=2&page=2")).json()
        # total reflects the full match set, not just the returned page.
        assert page2["total"] == 5
        assert page2["page"] == 2
        assert len(page2["products"]) == 2
        assert all("winter" in {lb["slug"] for lb in p["labels"]} for p in page2["products"])


class TestDynamicDefaultProductType:
    """Products created without a product_type get the default active type."""

    def test_create_without_type_uses_lowest_sort_order_active(self, app, db_path):
        from app.services import product_service

        product = product_service.create_product(
            {"id": "no-type", "name_en": "No Type", "price_cents": 1000, "stock": 1}
        )
        # candles has sort_order 0 → the default.
        assert product["product_type"] == "candles"

    def test_create_default_skips_deactivated_type(self, app, db_path):
        from app.services import product_service, taxonomy_service

        # Taxonomy term tables aren't reset by the module cleanup fixture, so
        # restore candles afterward to avoid leaking inactive state into later tests.
        taxonomy_service.update_term("product-types", "candles", {"is_active": False})
        try:
            product = product_service.create_product(
                {"id": "no-type-2", "name_en": "No Type 2", "price_cents": 1000, "stock": 1}
            )
            # candles is inactive → next active type (boxes) is chosen.
            assert product["product_type"] == "boxes"
        finally:
            taxonomy_service.update_term("product-types", "candles", {"is_active": True})


class TestSearchPagination:
    """The FTS search path returns an accurate total across pages."""

    @pytest.fixture()
    def _searchable(self, app, db_path):
        from app.services import product_service

        for i in range(5):
            product_service.create_product(
                {
                    "id": f"sp-{i}",
                    "name_en": f"Lavender Candle {i}",
                    "price_cents": 1000 + i,
                    "product_type": "candles",
                    "stock": 5,
                }
            )

    @pytest.mark.asyncio
    async def test_search_total_counts_all_matches(self, client, _searchable):
        body = (await client.get("/v1/products?q=lavender&limit=2&page=1")).json()
        assert body["total"] == 5
        assert len(body["products"]) == 2
