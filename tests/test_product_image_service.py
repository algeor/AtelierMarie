"""Tests for product image gallery service and migration behavior."""

import io

import pytest
from PIL import Image

from app.services import object_storage_service, product_image_service, product_service

_R2_PUBLIC_BASE = "https://cdn.test.example"


class _FakeStorageBackend:
    """In-memory storage backend (key -> bytes) for tests; no live bucket."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)


def _make_jpeg(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def fake_storage():
    """Inject an in-memory R2 backend and configure the public base URL."""
    from app.config import get_settings

    settings = get_settings()
    original_base = settings.r2_public_base_url
    settings.r2_public_base_url = _R2_PUBLIC_BASE
    backend = _FakeStorageBackend()
    object_storage_service.set_backend(backend)
    try:
        yield backend
    finally:
        object_storage_service.set_backend(None)
        settings.r2_public_base_url = original_base


@pytest.fixture()
def _product(db, fake_storage):
    product_service.create_product(
        {
            "id": "gallery-product",
            "name_en": "Gallery Product",
            "price_cents": 1000,
            "stock": 3,
        }
    )
    yield


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


def test_delete_image_unlinks_all_derivatives_including_zoom(_product, fake_storage):
    image = product_image_service.add_image("gallery-product", _make_jpeg())

    # Derive the R2 object keys from the stored public URLs.
    prefix = _R2_PUBLIC_BASE + "/"
    main_key = image["image_url"][len(prefix) :]
    thumb_key = image["thumbnail_url"][len(prefix) :]
    zoom_key = image["zoom_url"][len(prefix) :]
    assert main_key in fake_storage.objects
    assert thumb_key in fake_storage.objects
    assert zoom_key in fake_storage.objects

    product_image_service.delete_image("gallery-product", image["id"])

    assert main_key not in fake_storage.objects
    assert thumb_key not in fake_storage.objects
    assert zoom_key not in fake_storage.objects


def test_add_existing_image_url_stores_null_zoom(_product):
    result = product_image_service.add_existing_image_url(
        "gallery-product", "/static/products/externally-sourced.webp"
    )

    assert result is not None
    assert result["zoom_url"] is None

    product = product_service.get_product("gallery-product")
    assert product["images"][0]["zoom_url"] is None


def test_add_existing_image_variants_preserves_supplied_thumbnail_and_zoom(_product):
    result = product_image_service.add_existing_image_variants(
        "gallery-product",
        "/static/products/imported-main.webp",
        "/static/products/imported-thumb.webp",
        "/static/products/imported-zoom.webp",
    )

    assert result is not None
    assert result["image_url"] == "/static/products/imported-main.webp"
    assert result["thumbnail_url"] == "/static/products/imported-thumb.webp"
    assert result["zoom_url"] == "/static/products/imported-zoom.webp"


def test_delete_image_with_null_zoom_url_does_not_crash(_product):
    result = product_image_service.add_existing_image_url(
        "gallery-product", "/static/products/externally-sourced.webp"
    )
    assert result is not None

    # zoom_url is None for externally-sourced images; delete must tolerate it.
    product_image_service.delete_image("gallery-product", result["id"])

    assert product_image_service.list_images("gallery-product") == []


def test_deactivate_product_deletes_images(_product, fake_storage):
    """Soft-deleting a product removes its images entirely — rows AND objects.

    Deleting only the objects while keeping the ``product_images`` rows would let
    a later reactivation (``is_active=True``) point at media that no longer
    exists. So deactivation deletes the rows in the same operation, keeping rows
    and objects consistent.
    """
    image = product_image_service.add_image("gallery-product", _make_jpeg())
    second = product_image_service.add_image("gallery-product", _make_jpeg())

    prefix = _R2_PUBLIC_BASE + "/"
    expected_keys = {
        url[len(prefix) :]
        for img in (image, second)
        for url in (img["image_url"], img["thumbnail_url"], img["zoom_url"])
    }
    for key in expected_keys:
        assert key in fake_storage.objects

    product_service.deactivate_product("gallery-product")

    # Every variant object of every image is gone from the store...
    for key in expected_keys:
        assert key not in fake_storage.objects
    assert expected_keys.issubset(set(fake_storage.deleted))
    # ...and the product_images rows are gone too (no dangling rows to point a
    # reactivated product at deleted media).
    assert product_image_service.list_images("gallery-product") == []


def test_deactivate_product_survives_storage_failure(_product, monkeypatch):
    """Image-object cleanup is best-effort: a storage error never blocks deactivate.

    Deactivation is a Layer-1 admin operation; the R2 delete is fire-and-forget
    (logged, not fatal), so a storage outage must not stop the product being
    soft-deleted.
    """
    product_image_service.add_image("gallery-product", _make_jpeg())

    def boom(key):
        raise object_storage_service.MediaStorageError("R2 unavailable")

    monkeypatch.setattr(object_storage_service, "delete_object", boom)

    product = product_service.deactivate_product("gallery-product")

    assert product["is_active"] == 0
