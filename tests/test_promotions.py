"""Route + service tests for promotion campaigns, bulk discount, and banner.

Covers tasks 9.1–9.7: campaign CRUD/apply/remove, bulk discount validation and
partial failure, and the admin/public banner APIs.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_banner_singleton(app):
    """Restore the seeded ``site_banners`` singleton before each test.

    ``site_banners`` is a migration-seed table, so the root ``_clean_tables``
    autouse fixture deliberately never truncates it (its seeded row must persist
    across the template clone). Banner tests mutate that singleton, though, so
    without an explicit reset the mutations would leak between tests. This mirrors
    the per-file fresh-DB isolation the SQLite suite relied on.
    """
    from app.database import get_db

    with get_db() as conn:
        conn.execute(
            """
            UPDATE site_banners
            SET message_en = 'Free shipping on orders over €50 ✨',
                message_bg = 'Безплатна доставка за поръчки над 50€ ✨',
                link_label_en = NULL, link_label_bg = NULL, link_url = NULL,
                is_enabled = 1, starts_at = NULL, ends_at = NULL, version = 1
            WHERE id = 'default'
            """
        )
    yield


def _make_product(product_id: str, **overrides) -> None:
    from app.database import get_db
    from app.services import product_service

    # `category` is now a managed taxonomy slug (post dynamic-categories merge).
    # Ensure the referenced category term exists so create_product validation
    # passes and category_slug filtering works, mirroring real admin flow.
    category = overrides.pop("category", None)
    if category:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO product_categories (slug, name_en, sort_order) "
                "VALUES (%s, %s, 0) ON CONFLICT (slug) DO NOTHING",
                (category, category.replace("-", " ").title()),
            )

    data = {
        "id": product_id,
        "name_en": overrides.pop("name_en", product_id.replace("-", " ").title()),
        "price_cents": overrides.pop("price_cents", 3000),
        "stock": overrides.pop("stock", 10),
    }
    if category:
        data["category"] = category
    data.update(overrides)
    product_service.create_product(data)


def _get_discount(db, product_id: str) -> dict:
    row = db.execute(
        "SELECT discount_percent, discount_starts_at, discount_ends_at FROM products WHERE id = %s",
        (product_id,),
    ).fetchone()
    return {
        "percent": row["discount_percent"],
        "starts_at": row["discount_starts_at"],
        "ends_at": row["discount_ends_at"],
    }


# ---------------------------------------------------------------------------
# 9.1 Campaign CRUD + validation + auth
# ---------------------------------------------------------------------------


class TestCampaignCrud:
    @pytest.mark.asyncio
    async def test_requires_admin(self, client):
        response = await client.get("/v1/admin/promotions/campaigns")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_draft_with_explicit_products(self, admin_client):
        _make_product("a-candle")
        _make_product("b-candle")
        response = await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={
                "name": "Spring Sale",
                "discount_percent": 20,
                "product_ids": ["a-candle", "b-candle"],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Spring Sale"
        assert body["status"] == "draft"
        assert body["target_type"] == "ids"
        assert body["target_count"] == 2

    @pytest.mark.asyncio
    async def test_create_does_not_change_products(self, admin_client, db):
        _make_product("a-candle")
        await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={"name": "S", "discount_percent": 20, "product_ids": ["a-candle"]},
        )
        assert _get_discount(db, "a-candle")["percent"] is None

    @pytest.mark.asyncio
    async def test_create_scheduled_status(self, admin_client):
        _make_product("a-candle")
        response = await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={
                "name": "Future",
                "discount_percent": 15,
                "discount_starts_at": "2999-01-01 00:00:00",
                "discount_ends_at": "2999-02-01 00:00:00",
                "product_ids": ["a-candle"],
            },
        )
        assert response.status_code == 201
        body = response.json()
        # Spec: a created campaign with a future start reads as `scheduled`.
        assert body["status"] == "scheduled"
        assert body["discount_starts_at"] == "2999-01-01 00:00:00"
        assert body["discount_ends_at"] == "2999-02-01 00:00:00"

    @pytest.mark.asyncio
    async def test_reject_zero_percent(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={"name": "Bad", "discount_percent": 0, "product_ids": ["x"]},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_inverted_window(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={
                "name": "Bad",
                "discount_percent": 20,
                "discount_starts_at": "2999-02-01 00:00:00",
                "discount_ends_at": "2999-01-01 00:00:00",
                "product_ids": ["x"],
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_both_target_sources(self, admin_client):
        response = await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={
                "name": "Bad",
                "discount_percent": 20,
                "product_ids": ["x"],
                "filter": {"category": "luxury-jar"},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_and_detail(self, admin_client):
        _make_product("a-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={"name": "List Me", "discount_percent": 10, "product_ids": ["a-candle"]},
            )
        ).json()

        listing = await admin_client.get("/v1/admin/promotions/campaigns")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        detail = await admin_client.get(f"/v1/admin/promotions/campaigns/{created['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "List Me"

    @pytest.mark.asyncio
    async def test_detail_404(self, admin_client):
        response = await admin_client.get("/v1/admin/promotions/campaigns/missing")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_campaign(self, admin_client):
        _make_product("a-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={"name": "Orig", "discount_percent": 10, "product_ids": ["a-candle"]},
            )
        ).json()
        response = await admin_client.patch(
            f"/v1/admin/promotions/campaigns/{created['id']}",
            json={"name": "Renamed", "discount_percent": 25},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed"
        assert response.json()["discount_percent"] == 25

    @pytest.mark.asyncio
    async def test_delete_campaign(self, admin_client):
        _make_product("a-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={"name": "Bye", "discount_percent": 10, "product_ids": ["a-candle"]},
            )
        ).json()
        response = await admin_client.delete(f"/v1/admin/promotions/campaigns/{created['id']}")
        assert response.status_code == 204
        assert (
            await admin_client.get(f"/v1/admin/promotions/campaigns/{created['id']}")
        ).status_code == 404


# ---------------------------------------------------------------------------
# 9.2 Campaign apply
# ---------------------------------------------------------------------------


class TestCampaignApply:
    @pytest.mark.asyncio
    async def test_apply_explicit_targets(self, admin_client, db):
        _make_product("a-candle")
        _make_product("b-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={
                    "name": "Apply",
                    "discount_percent": 20,
                    "product_ids": ["a-candle", "b-candle"],
                },
            )
        ).json()
        response = await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/apply")
        assert response.status_code == 200
        assert response.json()["success_count"] == 2
        assert _get_discount(db, "a-candle")["percent"] == 20
        assert _get_discount(db, "b-candle")["percent"] == 20

        detail = (await admin_client.get(f"/v1/admin/promotions/campaigns/{created['id']}")).json()
        assert detail["status"] == "active"

    @pytest.mark.asyncio
    async def test_apply_filter_targets(self, admin_client, db):
        _make_product("spring-1", category="spring")
        _make_product("spring-2", category="spring")
        _make_product("other-1", category="woody")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={"name": "Filter", "discount_percent": 15, "filter": {"category": "spring"}},
            )
        ).json()
        response = await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/apply")
        assert response.status_code == 200
        assert response.json()["success_count"] == 2
        assert _get_discount(db, "spring-1")["percent"] == 15
        assert _get_discount(db, "other-1")["percent"] is None

    @pytest.mark.asyncio
    async def test_apply_partial_failure(self, admin_client, db):
        _make_product("a-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={
                    "name": "Partial",
                    "discount_percent": 20,
                    "product_ids": ["a-candle", "ghost"],
                },
            )
        ).json()
        response = await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/apply")
        body = response.json()
        assert body["success_count"] == 1
        assert body["failure_count"] == 1
        ghost = next(r for r in body["results"] if r["id"] == "ghost")
        assert ghost["status"] == "failed"
        assert _get_discount(db, "a-candle")["percent"] == 20

    @pytest.mark.asyncio
    async def test_apply_404(self, admin_client):
        response = await admin_client.post("/v1/admin/promotions/campaigns/missing/apply")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 9.3 Campaign remove (conservative)
# ---------------------------------------------------------------------------


class TestCampaignRemove:
    @pytest.mark.asyncio
    async def test_remove_clears_unchanged(self, admin_client, db):
        _make_product("a-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={"name": "Rm", "discount_percent": 20, "product_ids": ["a-candle"]},
            )
        ).json()
        await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/apply")
        response = await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/remove")
        assert response.status_code == 200
        assert response.json()["success_count"] == 1
        assert _get_discount(db, "a-candle")["percent"] is None

    @pytest.mark.asyncio
    async def test_remove_skips_edited_product(self, admin_client, db):
        _make_product("a-candle")
        created = (
            await admin_client.post(
                "/v1/admin/promotions/campaigns",
                json={"name": "Rm", "discount_percent": 20, "product_ids": ["a-candle"]},
            )
        ).json()
        await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/apply")
        # Manually change the product's discount after apply.
        await admin_client.patch("/v1/admin/products/a-candle", json={"discount_percent": 50})
        response = await admin_client.post(f"/v1/admin/promotions/campaigns/{created['id']}/remove")
        body = response.json()
        result = body["results"][0]
        assert result["status"] == "skipped"
        # The newer 50% discount is preserved.
        assert _get_discount(db, "a-candle")["percent"] == 50


# ---------------------------------------------------------------------------
# 9.4 / 9.5 Bulk discount endpoint
# ---------------------------------------------------------------------------


class TestBulkDiscount:
    @pytest.mark.asyncio
    async def test_requires_admin(self, client):
        response = await client.patch(
            "/v1/admin/products/bulk-discount",
            json={"operation": "apply", "product_ids": ["a"], "discount_percent": 20},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_apply_explicit(self, admin_client, db):
        _make_product("a-candle")
        _make_product("b-candle")
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={
                "operation": "apply",
                "product_ids": ["a-candle", "b-candle"],
                "discount_percent": 20,
            },
        )
        assert response.status_code == 200
        assert response.json()["success_count"] == 2
        assert _get_discount(db, "a-candle")["percent"] == 20

    @pytest.mark.asyncio
    async def test_remove_explicit(self, admin_client, db):
        _make_product("a-candle", discount_percent=30)
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={"operation": "remove", "product_ids": ["a-candle"]},
        )
        assert response.status_code == 200
        assert _get_discount(db, "a-candle") == {
            "percent": None,
            "starts_at": None,
            "ends_at": None,
        }

    @pytest.mark.asyncio
    async def test_reject_both_sources(self, admin_client):
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={
                "operation": "apply",
                "product_ids": ["a"],
                "filter": {"category": "x"},
                "discount_percent": 20,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_no_source(self, admin_client):
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={"operation": "apply", "discount_percent": 20},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_empty_ids(self, admin_client):
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={"operation": "apply", "product_ids": [], "discount_percent": 20},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_invalid_percent(self, admin_client, db):
        _make_product("a-candle")
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={"operation": "apply", "product_ids": ["a-candle"], "discount_percent": 100},
        )
        assert response.status_code == 422
        assert _get_discount(db, "a-candle")["percent"] is None

    @pytest.mark.asyncio
    async def test_reject_over_limit(self, admin_client, monkeypatch):
        from app.services import product_service

        monkeypatch.setattr(product_service, "BULK_DISCOUNT_TARGET_LIMIT", 1)
        _make_product("spring-1", category="spring")
        _make_product("spring-2", category="spring")
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={"operation": "apply", "filter": {"category": "spring"}, "discount_percent": 10},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "BULK_TARGET_LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_partial_failure(self, admin_client, db):
        _make_product("a-candle")
        _make_product("b-candle")
        response = await admin_client.patch(
            "/v1/admin/products/bulk-discount",
            json={
                "operation": "apply",
                "product_ids": ["a-candle", "missing", "b-candle"],
                "discount_percent": 20,
            },
        )
        body = response.json()
        assert body["success_count"] == 2
        assert body["failure_count"] == 1
        assert _get_discount(db, "a-candle")["percent"] == 20
        assert _get_discount(db, "b-candle")["percent"] == 20
        missing = next(r for r in body["results"] if r["id"] == "missing")
        assert missing["status"] == "failed"


# ---------------------------------------------------------------------------
# 9.6 Banner admin API
# ---------------------------------------------------------------------------


class TestBannerAdmin:
    @pytest.mark.asyncio
    async def test_requires_admin(self, client):
        assert (await client.get("/v1/admin/promotions/banner")).status_code == 401

    @pytest.mark.asyncio
    async def test_update_and_read(self, admin_client):
        response = await admin_client.put(
            "/v1/admin/promotions/banner",
            json={
                "message_en": "20% off spring candles",
                "message_bg": "20% отстъпка",
                "link_label_en": "Shop",
                "link_url": "/products",
                "is_enabled": True,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["message_en"] == "20% off spring candles"
        assert body["is_enabled"] is True

        read = (await admin_client.get("/v1/admin/promotions/banner")).json()
        assert read["message_en"] == "20% off spring candles"

    @pytest.mark.asyncio
    async def test_version_bumps_on_content_change(self, admin_client):
        first = (
            await admin_client.put(
                "/v1/admin/promotions/banner",
                json={"message_en": "First", "is_enabled": True},
            )
        ).json()
        second = (
            await admin_client.put(
                "/v1/admin/promotions/banner",
                json={"message_en": "Second", "is_enabled": True},
            )
        ).json()
        assert second["version"] > first["version"]

    @pytest.mark.asyncio
    async def test_reject_inverted_window(self, admin_client):
        response = await admin_client.put(
            "/v1/admin/promotions/banner",
            json={
                "message_en": "X",
                "is_enabled": True,
                "starts_at": "2999-02-01 00:00:00",
                "ends_at": "2999-01-01 00:00:00",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_enable_without_message(self, admin_client):
        response = await admin_client.put(
            "/v1/admin/promotions/banner",
            json={"is_enabled": True},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_unsafe_link_url(self, admin_client):
        response = await admin_client.put(
            "/v1/admin/promotions/banner",
            json={
                "message_en": "Sale",
                "link_url": "javascript:alert(1)",
                "is_enabled": True,
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 9.7 Public banner API
# ---------------------------------------------------------------------------


class TestPublicBanner:
    @pytest.mark.asyncio
    async def test_active_banner_en(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={"message_en": "20% off spring candles", "is_enabled": True},
        )
        response = await client.get("/v1/promotions/banner?locale=en")
        assert response.status_code == 200
        banner = response.json()["banner"]
        assert banner["message"] == "20% off spring candles"
        assert banner["dismiss_key"]

    @pytest.mark.asyncio
    async def test_bg_fallback_to_en(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={"message_en": "English only", "is_enabled": True},
        )
        response = await client.get("/v1/promotions/banner?locale=bg")
        assert response.json()["banner"]["message"] == "English only"

    @pytest.mark.asyncio
    async def test_bg_localized(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={"message_en": "EN", "message_bg": "BG текст", "is_enabled": True},
        )
        response = await client.get("/v1/promotions/banner?locale=bg")
        assert response.json()["banner"]["message"] == "BG текст"

    @pytest.mark.asyncio
    async def test_disabled_hidden(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={"message_en": "Hidden", "is_enabled": False},
        )
        response = await client.get("/v1/promotions/banner")
        assert response.json()["banner"] is None

    @pytest.mark.asyncio
    async def test_future_hidden(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={
                "message_en": "Later",
                "is_enabled": True,
                "starts_at": "2999-01-01 00:00:00",
            },
        )
        response = await client.get("/v1/promotions/banner")
        assert response.json()["banner"] is None

    @pytest.mark.asyncio
    async def test_expired_hidden(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={
                "message_en": "Old",
                "is_enabled": True,
                "ends_at": "2000-01-01 00:00:00",
            },
        )
        response = await client.get("/v1/promotions/banner")
        assert response.json()["banner"] is None

    @pytest.mark.asyncio
    async def test_link_returned(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/promotions/banner",
            json={
                "message_en": "Sale",
                "link_label_en": "Shop now",
                "link_url": "/products",
                "is_enabled": True,
            },
        )
        banner = (await client.get("/v1/promotions/banner")).json()["banner"]
        assert banner["link_url"] == "/products"
        assert banner["link_label"] == "Shop now"

    @pytest.mark.asyncio
    async def test_legacy_unsafe_link_not_served(self, client, db):
        db.execute(
            """
            UPDATE site_banners
            SET message_en = %s, link_label_en = %s, link_url = %s, is_enabled = 1, version = 2
            WHERE id = 'default'
            """,
            ("Sale", "Shop now", "javascript:alert(1)"),
        )
        db.commit()

        banner = (await client.get("/v1/promotions/banner")).json()["banner"]
        assert banner["message"] == "Sale"
        assert banner["link_label"] == "Shop now"
        assert banner["link_url"] is None


# ---------------------------------------------------------------------------
# Review follow-ups: status derivation, atomic/conservative edges, guards
# ---------------------------------------------------------------------------


async def _create_campaign(admin_client, **body) -> dict:
    body.setdefault("name", "C")
    body.setdefault("discount_percent", 20)
    body.setdefault("product_ids", ["a-candle"])
    return (await admin_client.post("/v1/admin/promotions/campaigns", json=body)).json()


class TestStatusDerivation:
    @pytest.mark.asyncio
    async def test_applied_within_window_is_active(self, admin_client):
        _make_product("a-candle")
        c = await _create_campaign(admin_client)
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        detail = (await admin_client.get(f"/v1/admin/promotions/campaigns/{c['id']}")).json()
        assert detail["status"] == "active"

    @pytest.mark.asyncio
    async def test_applied_past_end_is_ended(self, admin_client):
        _make_product("a-candle")
        c = await _create_campaign(
            admin_client,
            discount_starts_at="2000-01-01 00:00:00",
            discount_ends_at="2000-02-01 00:00:00",
        )
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        detail = (await admin_client.get(f"/v1/admin/promotions/campaigns/{c['id']}")).json()
        assert detail["status"] == "ended"


class TestCampaignUpdateEdges:
    @pytest.mark.asyncio
    async def test_switch_ids_to_filter(self, admin_client):
        _make_product("a-candle", category="spring")
        _make_product("b-candle", category="spring")
        c = await _create_campaign(admin_client, product_ids=["a-candle"])
        resp = await admin_client.patch(
            f"/v1/admin/promotions/campaigns/{c['id']}",
            json={"filter": {"category": "spring"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["target_type"] == "filter"
        assert body["target_count"] == 2

    @pytest.mark.asyncio
    async def test_update_invalid_window_422(self, admin_client):
        _make_product("a-candle")
        c = await _create_campaign(
            admin_client,
            discount_starts_at="2999-01-01 00:00:00",
            discount_ends_at="2999-02-01 00:00:00",
        )
        resp = await admin_client.patch(
            f"/v1/admin/promotions/campaigns/{c['id']}",
            json={"discount_starts_at": "2999-03-01 00:00:00"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_empty_filter_on_create(self, admin_client):
        resp = await admin_client.post(
            "/v1/admin/promotions/campaigns",
            json={"name": "All", "discount_percent": 10, "filter": {}},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_edit_discount_on_applied_campaign_blocked(self, admin_client):
        _make_product("a-candle")
        c = await _create_campaign(admin_client)
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        # Applied (active) campaign: changing the discount must be rejected.
        resp = await admin_client.patch(
            f"/v1/admin/promotions/campaigns/{c['id']}",
            json={"discount_percent": 50},
        )
        assert resp.status_code == 409
        # Renaming an applied campaign is still allowed.
        resp2 = await admin_client.patch(
            f"/v1/admin/promotions/campaigns/{c['id']}",
            json={"name": "Renamed"},
        )
        assert resp2.status_code == 200


class TestApplyRemoveEdges:
    @pytest.mark.asyncio
    async def test_apply_over_limit_route(self, admin_client, monkeypatch):
        from app.services import product_service

        monkeypatch.setattr(product_service, "BULK_DISCOUNT_TARGET_LIMIT", 1)
        _make_product("spring-1", category="spring")
        _make_product("spring-2", category="spring")
        c = await _create_campaign(admin_client, product_ids=None, filter={"category": "spring"})
        resp = await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "BULK_TARGET_LIMIT_EXCEEDED"
        # No partial apply: campaign stays draft.
        detail = (await admin_client.get(f"/v1/admin/promotions/campaigns/{c['id']}")).json()
        assert detail["status"] == "draft"

    @pytest.mark.asyncio
    async def test_remove_after_product_deleted(self, admin_client, db):
        _make_product("a-candle")
        c = await _create_campaign(admin_client)
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        await admin_client.delete("/v1/admin/products/a-candle")  # soft-delete keeps the row
        # Hard-delete the product row to hit the "product gone" branch.
        db.execute("DELETE FROM products WHERE id = 'a-candle'")
        db.commit()
        resp = await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/remove")
        assert resp.status_code == 200
        assert resp.json()["results"][0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_delete_applied_campaign_preserves_discount(self, admin_client, db):
        _make_product("a-candle")
        c = await _create_campaign(admin_client)
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        assert _get_discount(db, "a-candle")["percent"] == 20
        await admin_client.delete(f"/v1/admin/promotions/campaigns/{c['id']}")
        # Deleting the campaign record leaves the product discount untouched.
        assert _get_discount(db, "a-candle")["percent"] == 20

    @pytest.mark.asyncio
    async def test_last_result_persisted_in_detail(self, admin_client):
        _make_product("a-candle")
        c = await _create_campaign(admin_client)
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        detail = (await admin_client.get(f"/v1/admin/promotions/campaigns/{c['id']}")).json()
        assert detail["last_result"]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_remove_all_skipped_marks_campaign_removed(self, admin_client, db):
        _make_product("a-candle")
        c = await _create_campaign(admin_client)
        await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/apply")
        await admin_client.patch("/v1/admin/products/a-candle", json={"discount_percent": 50})

        resp = await admin_client.post(f"/v1/admin/promotions/campaigns/{c['id']}/remove")
        assert resp.status_code == 200
        assert resp.json()["results"][0]["status"] == "skipped"
        assert _get_discount(db, "a-candle")["percent"] == 50

        detail = (await admin_client.get(f"/v1/admin/promotions/campaigns/{c['id']}")).json()
        assert detail["status"] == "removed"


class TestPromotionSchemaMigration:
    def test_existing_campaign_table_gets_last_result_column(self, db):
        # The legacy SQLite ``init_db`` add-column migration path is gone under
        # Postgres: ``last_result`` ships in the initial migration. Assert the
        # real schema exposes the column and it defaults to NULL for a row that
        # does not set it (preserving the original intent).
        db.execute(
            """
            INSERT INTO promotion_campaigns (
                id, name, discount_percent, target_type, target_ids,
                created_at, updated_at
            ) VALUES (
                'legacy-campaign', 'Legacy', 20, 'ids', '["a-candle"]',
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            r["column_name"]
            for r in db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'promotion_campaigns'"
            ).fetchall()
        }
        row = db.execute(
            "SELECT last_result FROM promotion_campaigns WHERE id = %s",
            ("legacy-campaign",),
        ).fetchone()

        assert "last_result" in columns
        assert row["last_result"] is None


class TestBannerEdges:
    @pytest.mark.asyncio
    async def test_version_not_bumped_on_noop_save(self, admin_client):
        first = (
            await admin_client.put(
                "/v1/admin/promotions/banner",
                json={"message_en": "Same", "is_enabled": True},
            )
        ).json()
        second = (
            await admin_client.put(
                "/v1/admin/promotions/banner",
                json={"message_en": "Same", "is_enabled": True},
            )
        ).json()
        assert second["version"] == first["version"]

    @pytest.mark.asyncio
    async def test_default_seeded_banner_is_visible(self, client):
        # Between tests the singleton is reset to the seeded (enabled) default.
        banner = (await client.get("/v1/promotions/banner")).json()["banner"]
        assert banner is not None
        assert "shipping" in banner["message"].lower()
