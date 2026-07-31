"""Route tests for public and admin atelier story APIs."""

import io

import pytest
from PIL import Image


def _make_jpeg(width: int = 96, height: int = 96) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buffer, format="JPEG")
    return buffer.getvalue()


class TestPublicAbout:
    @pytest.mark.asyncio
    async def test_get_about_shape_and_order(self, client):
        response = await client.get("/v1/about?locale=bg")

        assert response.status_code == 200
        body = response.json()
        assert [section["slug"] for section in body["sections"]][:3] == [
            "hero",
            "story",
            "philosophy",
        ]
        hero = body["sections"][0]
        assert hero["type"] == "hero"
        assert hero["cta"] == {"label": "Разгледайте нашата колекция", "href": "/products"}
        assert isinstance(hero["items"], list)

    @pytest.mark.asyncio
    async def test_hidden_sections_and_items_are_excluded(self, admin_client, client):
        await admin_client.patch(
            "/v1/admin/about/sections/philosophy/publish", json={"is_published": False}
        )
        about = (await client.get("/v1/about")).json()
        assert "philosophy" not in [section["slug"] for section in about["sections"]]

        process = next(section for section in about["sections"] if section["slug"] == "process")
        item_id = process["items"][0]["id"]
        await admin_client.patch(
            f"/v1/admin/about/sections/process/items/{item_id}/publish",
            json={"is_published": False},
        )
        updated = (await client.get("/v1/about")).json()
        process = next(section for section in updated["sections"] if section["slug"] == "process")
        assert item_id not in [item["id"] for item in process["items"]]


class TestAdminAbout:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        response = await client.get("/v1/admin/about")
        assert response.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_section_patch_item_crud_reorder_and_publish(self, admin_client):
        patch = await admin_client.patch(
            "/v1/admin/about/sections/hero",
            json={"heading_bg": "Ново заглавие"},
        )
        assert patch.status_code == 200
        assert patch.json()["heading_bg"] == "Ново заглавие"

        create = await admin_client.post(
            "/v1/admin/about/sections/values/items",
            json={"title_en": "Simplicity", "text_en": "Quiet detail."},
        )
        assert create.status_code == 201
        item = create.json()

        update = await admin_client.patch(
            f"/v1/admin/about/sections/values/items/{item['id']}",
            json={"title_bg": "Простота"},
        )
        assert update.status_code == 200
        assert update.json()["title_bg"] == "Простота"

        listing = (await admin_client.get("/v1/admin/about")).json()
        values = next(section for section in listing["sections"] if section["slug"] == "values")
        reversed_ids = [item["id"] for item in reversed(values["items"])]
        reorder = await admin_client.post(
            "/v1/admin/about/sections/values/items/reorder", json={"ids": reversed_ids}
        )
        assert reorder.status_code == 200
        assert [item["id"] for item in reorder.json()] == reversed_ids

        publish = await admin_client.patch(
            f"/v1/admin/about/sections/values/items/{item['id']}/publish",
            json={"is_published": False},
        )
        assert publish.status_code == 200
        assert publish.json()["is_published"] is False

        delete = await admin_client.delete(f"/v1/admin/about/sections/values/items/{item['id']}")
        assert delete.status_code == 204

    @pytest.mark.asyncio
    async def test_section_reorder_validation_and_success(self, admin_client):
        invalid = await admin_client.post(
            "/v1/admin/about/sections/reorder", json={"slugs": ["hero"]}
        )
        assert invalid.status_code == 409

        listing = (await admin_client.get("/v1/admin/about")).json()
        slugs = [section["slug"] for section in listing["sections"]]
        reordered = list(reversed(slugs))
        response = await admin_client.post(
            "/v1/admin/about/sections/reorder", json={"slugs": reordered}
        )
        assert response.status_code == 200
        assert [section["slug"] for section in response.json()] == reordered

    @pytest.mark.asyncio
    async def test_image_upload_invalid_and_clear(self, admin_client, tmp_path):
        from app.config import get_settings

        invalid = await admin_client.post(
            "/v1/admin/about/sections/hero/image",
            files={"file": ("not.txt", b"not an image", "text/plain")},
        )
        assert invalid.status_code == 422

        settings = get_settings()
        original = settings.static_file_path
        settings.static_file_path = str(tmp_path)
        try:
            upload = await admin_client.post(
                "/v1/admin/about/sections/hero/image",
                files={"file": ("hero.jpg", _make_jpeg(), "image/jpeg")},
            )
        finally:
            settings.static_file_path = original

        assert upload.status_code == 200
        assert upload.json()["image_id"]
        assert upload.json()["image"].startswith("/static/products/about-hero_")

        clear = await admin_client.delete("/v1/admin/about/sections/hero/image")
        assert clear.status_code == 200
        assert clear.json()["image_id"] is None
