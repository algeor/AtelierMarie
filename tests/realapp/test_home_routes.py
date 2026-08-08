"""Route tests for public and admin homepage content APIs."""

import io

import pytest
from PIL import Image

from tests.conftest import R2_TEST_PUBLIC_BASE


def _make_jpeg(width: int = 96, height: int = 96) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buffer, format="JPEG")
    return buffer.getvalue()


class TestPublicHome:
    @pytest.mark.asyncio
    async def test_get_home_shape_and_order(self, client):
        response = await client.get("/v1/home?locale=bg")

        assert response.status_code == 200
        body = response.json()
        assert [section["slug"] for section in body["sections"]] == [
            "hero",
            "featured",
            "trust",
            "categories",
        ]
        hero = body["sections"][0]
        assert hero["type"] == "hero"
        assert hero["cta"] == {"label": "Разгледай колекцията", "href": "/products"}

    @pytest.mark.asyncio
    async def test_hidden_sections_and_items_are_excluded(self, admin_client, client):
        await admin_client.patch(
            "/v1/admin/home/sections/categories/publish", json={"is_published": False}
        )
        home = (await client.get("/v1/home")).json()
        assert "categories" not in [section["slug"] for section in home["sections"]]

        trust = next(section for section in home["sections"] if section["slug"] == "trust")
        item_id = trust["items"][0]["id"]
        await admin_client.patch(
            f"/v1/admin/home/sections/trust/items/{item_id}/publish",
            json={"is_published": False},
        )
        updated = (await client.get("/v1/home")).json()
        trust = next(section for section in updated["sections"] if section["slug"] == "trust")
        assert item_id not in [item["id"] for item in trust["items"]]


class TestAdminHome:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        response = await client.get("/v1/admin/home")
        assert response.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_section_patch_item_crud_reorder_and_publish(self, admin_client):
        patch = await admin_client.patch(
            "/v1/admin/home/sections/hero",
            json={"heading_bg": "Ново заглавие"},
        )
        assert patch.status_code == 200
        assert patch.json()["heading_bg"] == "Ново заглавие"

        create = await admin_client.post(
            "/v1/admin/home/sections/trust/items",
            json={"title_en": "Small batches", "text_en": "Quiet detail."},
        )
        assert create.status_code == 201
        item = create.json()

        update = await admin_client.patch(
            f"/v1/admin/home/sections/trust/items/{item['id']}",
            json={"title_bg": "Малки серии"},
        )
        assert update.status_code == 200
        assert update.json()["title_bg"] == "Малки серии"

        listing = (await admin_client.get("/v1/admin/home")).json()
        trust = next(section for section in listing["sections"] if section["slug"] == "trust")
        reversed_ids = [item["id"] for item in reversed(trust["items"])]
        reorder = await admin_client.post(
            "/v1/admin/home/sections/trust/items/reorder", json={"ids": reversed_ids}
        )
        assert reorder.status_code == 200
        assert [item["id"] for item in reorder.json()] == reversed_ids

        publish = await admin_client.patch(
            f"/v1/admin/home/sections/trust/items/{item['id']}/publish",
            json={"is_published": False},
        )
        assert publish.status_code == 200
        assert publish.json()["is_published"] is False

        delete = await admin_client.delete(f"/v1/admin/home/sections/trust/items/{item['id']}")
        assert delete.status_code == 204

    @pytest.mark.asyncio
    async def test_section_reorder_validation_and_success(self, admin_client):
        invalid = await admin_client.post(
            "/v1/admin/home/sections/reorder", json={"slugs": ["hero"]}
        )
        assert invalid.status_code == 409

        listing = (await admin_client.get("/v1/admin/home")).json()
        slugs = [section["slug"] for section in listing["sections"]]
        reordered = list(reversed(slugs))
        response = await admin_client.post(
            "/v1/admin/home/sections/reorder", json={"slugs": reordered}
        )
        assert response.status_code == 200
        assert [section["slug"] for section in response.json()] == reordered

    @pytest.mark.asyncio
    async def test_image_upload_invalid_and_clear(self, admin_client, fake_storage):
        invalid = await admin_client.post(
            "/v1/admin/home/sections/hero/image",
            files={"file": ("not.txt", b"not an image", "text/plain")},
        )
        assert invalid.status_code == 422

        upload = await admin_client.post(
            "/v1/admin/home/sections/hero/image",
            files={"file": ("hero.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert upload.status_code == 200
        image_id = upload.json()["image_id"]
        assert image_id
        expected_url = f"{R2_TEST_PUBLIC_BASE}/products/home-hero_{image_id}.webp"
        assert upload.json()["image"] == expected_url
        assert f"products/home-hero_{image_id}.webp" in fake_storage.objects

        clear = await admin_client.delete("/v1/admin/home/sections/hero/image")
        assert clear.status_code == 200
        assert clear.json()["image_id"] is None
