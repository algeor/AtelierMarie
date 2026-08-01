"""Integration tests for Cookie Policy public and admin endpoints."""

import pytest


class TestPublicCookiesRoutes:
    @pytest.mark.asyncio
    async def test_public_get_returns_localized_cookies(self, client):
        resp = await client.get("/v1/cookies?locale=bg")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Политика за бисквитки"
        assert any(item["name"] == "atelier_cookie_consent" for item in body["cookies"])

    @pytest.mark.asyncio
    async def test_unknown_locale_defaults_to_english(self, client):
        resp = await client.get("/v1/cookies?locale=fr")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Cookie Policy"


class TestAdminCookiesRoutes:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        assert (await client.get("/v1/admin/cookies")).status_code == 401
        page = await client.patch("/v1/admin/cookies/page", json={"title_en": "X"})
        assert page.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_patch_page_inventory_and_section(self, admin_client, client):
        page = await admin_client.patch(
            "/v1/admin/cookies/page",
            json={"title_en": "Cookie details", "title_bg": "Данни за бисквитки"},
        )
        assert page.status_code == 200
        assert page.json()["title_en"] == "Cookie details"

        inventory = await admin_client.patch(
            "/v1/admin/cookies/inventory/atelier_cookie_consent",
            json={"purpose_en": "Stores consent choice."},
        )
        assert inventory.status_code == 200
        assert inventory.json()["purpose_en"] == "Stores consent choice."
        assert inventory.json()["source"] == "seed"

        section = await admin_client.patch(
            "/v1/admin/cookies/sections/control",
            json={"body_en": ["One", "Two"], "body_bg": ["Едно"]},
        )
        assert section.status_code == 200
        assert section.json()["body_en"] == ["One", "Two"]

        public = await client.get("/v1/cookies?locale=bg")
        assert public.status_code == 200
        assert public.json()["title"] == "Данни за бисквитки"
        control = next(
            section for section in public.json()["sections"] if section["id"] == "control"
        )
        assert control["body"] == ["Едно"]

    @pytest.mark.asyncio
    async def test_blank_required_section_body_returns_422(self, admin_client):
        resp = await admin_client.patch("/v1/admin/cookies/sections/control", json={"body_en": []})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "invalid_cookies"
