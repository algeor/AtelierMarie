"""Integration tests for Privacy Policy public and admin endpoints."""

import pytest


class TestPublicPrivacyRoutes:
    @pytest.mark.asyncio
    async def test_public_get_returns_localized_privacy(self, client):
        resp = await client.get("/v1/privacy?locale=bg")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Политика за поверителност"
        assert body["controller_title"] == "Данни за администратора"
        assert any(section["id"] == "rights" for section in body["sections"])

    @pytest.mark.asyncio
    async def test_unknown_locale_defaults_to_english(self, client):
        resp = await client.get("/v1/privacy?locale=fr")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Privacy Policy"


class TestAdminPrivacyRoutes:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        assert (await client.get("/v1/admin/privacy")).status_code == 401
        page = await client.patch("/v1/admin/privacy/page", json={"title_en": "X"})
        assert page.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_patch_page_and_section(self, admin_client, client):
        page = await admin_client.patch(
            "/v1/admin/privacy/page",
            json={"title_en": "Privacy details", "title_bg": "Данни за поверителност"},
        )
        assert page.status_code == 200
        assert page.json()["title_en"] == "Privacy details"

        section = await admin_client.patch(
            "/v1/admin/privacy/sections/rights",
            json={"body_en": ["One", "Two"], "body_bg": ["Едно"]},
        )
        assert section.status_code == 200
        assert section.json()["body_en"] == ["One", "Two"]

        public = await client.get("/v1/privacy?locale=bg")
        assert public.status_code == 200
        assert public.json()["title"] == "Данни за поверителност"
        rights = next(section for section in public.json()["sections"] if section["id"] == "rights")
        assert rights["body"] == ["Едно"]

    @pytest.mark.asyncio
    async def test_blank_required_section_body_returns_422(self, admin_client):
        resp = await admin_client.patch("/v1/admin/privacy/sections/rights", json={"body_en": []})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "invalid_privacy"
