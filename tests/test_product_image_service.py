"""Tests for product image gallery service and migration behavior."""

import io
from pathlib import Path

import pytest
from PIL import Image

from app.services import product_image_service, product_service


def _make_jpeg(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def _product(db, tmp_path, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    original = settings.static_file_path
    settings.static_file_path = str(tmp_path)
    product_service.create_product(
        {
            "id": "gallery-product",
            "name_en": "Gallery Product",
            "price_cents": 1000,
            "stock": 3,
        }
    )
    yield
    settings.static_file_path = original


def test_first_image_is_primary_and_response_fields_are_assembled(_product):
    image = product_image_service.add_image("gallery-product", _make_jpeg())

    assert image["is_primary"] is True
    product = product_service.get_product("gallery-product")
    assert product["images"] == [image]
    assert product["primary_image_url"] == image["image_url"]
    assert "image_url" not in product


def test_append_cap_is_enforced(_product):
    for _ in range(product_image_service.MAX_IMAGES_PER_PRODUCT):
        product_image_service.add_image("gallery-product", _make_jpeg())

    with pytest.raises(product_image_service.ProductImageLimitError):
        product_image_service.add_image("gallery-product", _make_jpeg())


def test_reorder_preserves_primary(_product):
    first = product_image_service.add_image("gallery-product", _make_jpeg())
    second = product_image_service.add_image("gallery-product", _make_jpeg())

    reordered = product_image_service.reorder_images(
        "gallery-product",
        [second["id"], first["id"]],
    )

    assert [image["id"] for image in reordered] == [second["id"], first["id"]]
    assert next(image for image in reordered if image["id"] == first["id"])["is_primary"] is True


def test_set_primary_and_delete_primary_promotes_lowest_order(_product):
    first = product_image_service.add_image("gallery-product", _make_jpeg())
    second = product_image_service.add_image("gallery-product", _make_jpeg())

    promoted = product_image_service.set_primary("gallery-product", second["id"])
    assert promoted["is_primary"] is True

    product_image_service.delete_image("gallery-product", second["id"])
    remaining = product_image_service.list_images("gallery-product")
    assert remaining == [{**first, "is_primary": True}]


def test_delete_image_unlinks_all_derivatives_including_zoom(_product, tmp_path):
    image = product_image_service.add_image("gallery-product", _make_jpeg())
    main_path = tmp_path / "products" / Path(image["image_url"]).name
    thumb_path = tmp_path / "products" / Path(image["thumbnail_url"]).name
    zoom_path = tmp_path / "products" / Path(image["zoom_url"]).name
    assert main_path.exists()
    assert thumb_path.exists()
    assert zoom_path.exists()

    product_image_service.delete_image("gallery-product", image["id"])

    assert not main_path.exists()
    assert not thumb_path.exists()
    assert not zoom_path.exists()


def test_add_existing_image_url_stores_null_zoom(_product):
    result = product_image_service.add_existing_image_url(
        "gallery-product", "/static/products/externally-sourced.webp"
    )

    assert result is not None
    assert result["zoom_url"] is None

    product = product_service.get_product("gallery-product")
    assert product["images"][0]["zoom_url"] is None


def test_delete_image_with_null_zoom_url_does_not_crash(_product):
    result = product_image_service.add_existing_image_url(
        "gallery-product", "/static/products/externally-sourced.webp"
    )
    assert result is not None

    # zoom_url is None for externally-sourced images; delete must tolerate it.
    product_image_service.delete_image("gallery-product", result["id"])

    assert product_image_service.list_images("gallery-product") == []
