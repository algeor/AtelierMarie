"""Integration tests for FAQ public and admin endpoints."""

import pytest


class TestPublicFaqRoutes:
    @pytest.mark.asyncio
    async def test_public_get_returns_localized_seeded_sections(self, client):
        resp = await client.get("/v1/faq?locale=bg")
        assert resp.status_code == 200
        body = resp.json()
        assert [section["slug"] for section in body["sections"]] == [
            "candles",
            "care",
            "custom",
            "shipping",
        ]
        candles = body["sections"][0]
        assert candles["title"] == "За нашите свещи"
        assert candles["items"][0]["question"] == "Ръчно изработени ли са вашите свещи?"

    @pytest.mark.asyncio
    async def test_unknown_locale_defaults_to_english(self, client):
        resp = await client.get("/v1/faq?locale=fr")
        assert resp.status_code == 200
        assert resp.json()["sections"][0]["title"] == "About Our Candles"


class TestAdminFaqRoutes:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        assert (await client.get("/v1/admin/faq")).status_code == 401
        assert (
            await client.post(
                "/v1/admin/faq",
                json={"section": "care", "question_en": "Q", "answer_en": "A"},
            )
        ).status_code == 401
        assert (await client.delete("/v1/admin/faq/items/1")).status_code == 401

    @pytest.mark.asyncio
    async def test_admin_crud_reorder_and_section_patch(self, admin_client, client):
        create = await admin_client.post(
            "/v1/admin/faq",
            json={
                "section": "care",
                "question_en": "Will raw text stay raw?",
                "answer_en": "We'd keep Care & Safety—plain text.\n\n* First",
                "question_bg": "BG raw?",
                "answer_bg": "BG answer",
            },
        )
        assert create.status_code == 201
        item = create.json()
        assert item["is_published"] is True

        update = await admin_client.patch(
            f"/v1/admin/faq/items/{item['id']}",
            json={"is_published": False, "answer_bg": "Updated BG"},
        )
        assert update.status_code == 200
        assert update.json()["is_published"] is False

        public_hidden = await client.get("/v1/faq?locale=en")
        care_items = next(
            section["items"]
            for section in public_hidden.json()["sections"]
            if section["slug"] == "care"
        )
        assert item["id"] not in {faq_item["id"] for faq_item in care_items}

        listing = await admin_client.get("/v1/admin/faq")
        assert listing.status_code == 200
        care = next(section for section in listing.json()["sections"] if section["slug"] == "care")
        ordered_ids = [faq_item["id"] for faq_item in care["items"]]
        reorder = await admin_client.patch(
            "/v1/admin/faq/reorder",
            json={"section": "care", "ordered_ids": list(reversed(ordered_ids))},
        )
        assert reorder.status_code == 200
        reordered_care = next(
            section for section in reorder.json()["sections"] if section["slug"] == "care"
        )
        assert [faq_item["id"] for faq_item in reordered_care["items"]] == list(
            reversed(ordered_ids)
        )

        section_patch = await admin_client.patch(
            "/v1/admin/faq/sections/care", json={"title_en": "Care Updated"}
        )
        assert section_patch.status_code == 200
        assert section_patch.json()["slug"] == "care"
        assert section_patch.json()["title_en"] == "Care Updated"

        delete = await admin_client.delete(f"/v1/admin/faq/items/{item['id']}")
        assert delete.status_code == 204

    @pytest.mark.asyncio
    async def test_invalid_section_returns_422(self, admin_client):
        resp = await admin_client.post(
            "/v1/admin/faq",
            json={"section": "missing", "question_en": "Q", "answer_en": "A"},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_FAQ"
