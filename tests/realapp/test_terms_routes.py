"""Integration tests for Terms public and admin endpoints."""

import pytest


class TestPublicTermsRoutes:
    @pytest.mark.asyncio
    async def test_public_get_returns_localized_terms(self, client):
        resp = await client.get("/v1/terms?locale=bg")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Общи условия"
        assert any(section["id"] == "returns" for section in body["sections"])

    @pytest.mark.asyncio
    async def test_unknown_locale_defaults_to_english(self, client):
        resp = await client.get("/v1/terms?locale=fr")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Terms & Conditions"


class TestAdminTermsRoutes:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        assert (await client.get("/v1/admin/terms")).status_code == 401
        page = await client.patch("/v1/admin/terms/page", json={"title_en": "X"})
        assert page.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_patch_page_and_section(self, admin_client, client):
        page = await admin_client.patch(
            "/v1/admin/terms/page",
            json={"title_en": "Legal terms", "title_bg": "Правни условия"},
        )
        assert page.status_code == 200
        assert page.json()["title_en"] == "Legal terms"

        section = await admin_client.patch(
            "/v1/admin/terms/sections/returns",
            json={"body_en": ["One", "Two"], "body_bg": ["Едно"]},
        )
        assert section.status_code == 200
        assert section.json()["body_en"] == ["One", "Two"]

        public = await client.get("/v1/terms?locale=bg")
        assert public.status_code == 200
        assert public.json()["title"] == "Правни условия"
        returns = next(
            section for section in public.json()["sections"] if section["id"] == "returns"
        )
        assert returns["body"] == ["Едно"]

    @pytest.mark.asyncio
    async def test_blank_required_section_body_returns_422(self, admin_client):
        resp = await admin_client.patch("/v1/admin/terms/sections/returns", json={"body_en": []})
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "invalid_terms"
