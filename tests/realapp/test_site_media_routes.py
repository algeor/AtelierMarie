"""Route tests for admin-managed site media."""

from io import BytesIO

import pytest
from PIL import Image


def _make_jpeg(width: int = 96, height: int = 96) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(180, 120, 120)).save(buffer, format="JPEG")
    return buffer.getvalue()


class TestSiteMediaRoutes:
    @pytest.mark.asyncio
    async def test_public_returns_effective_defaults(self, client):
        response = await client.get("/v1/site-media")

        assert response.status_code == 200
        assets = response.json()["assets"]
        assert assets["home_hero"] is None
        assert assets["error_page_image"] == "/rebrand/error-candle.webp"

    @pytest.mark.asyncio
    async def test_admin_upload_invalid_and_clear(self, admin_client, tmp_path):
        from app.config import get_settings

        invalid = await admin_client.post(
            "/v1/admin/site-media/assets/home_hero/image",
            files={"file": ("not.txt", b"not an image", "text/plain")},
        )
        assert invalid.status_code == 422

        settings = get_settings()
        original = settings.static_file_path
        settings.static_file_path = str(tmp_path)
        try:
            upload = await admin_client.post(
                "/v1/admin/site-media/assets/home_hero/image",
                files={"file": ("hero.jpg", _make_jpeg(), "image/jpeg")},
            )

            assert upload.status_code == 200
            assert upload.json()["image_id"]
            assert upload.json()["image_url"].startswith("/static/products/site-media-home-hero_")

            public = await admin_client.get("/v1/site-media")
            assert public.json()["assets"]["home_hero"] == upload.json()["image_url"]

            clear = await admin_client.delete("/v1/admin/site-media/assets/home_hero/image")
        finally:
            settings.static_file_path = original

        assert clear.status_code == 200
        assert clear.json()["image_id"] is None
        assert clear.json()["effective_url"] is None

    @pytest.mark.asyncio
    async def test_admin_requires_auth(self, client):
        response = await client.get("/v1/admin/site-media")

        assert response.status_code == 401
