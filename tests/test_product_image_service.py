"""Tests for product image gallery service and migration behavior."""

import io
import sqlite3

import pytest
from PIL import Image

from app.database import get_db, init_db
from app.services import product_image_service, product_service


def _make_jpeg(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def _product(db_path, tmp_path, monkeypatch):
    init_db(db_path)
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


def test_migration_moves_legacy_image_url_and_drops_column(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE products (
            id TEXT PRIMARY KEY,
            name_en TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK(price_cents > 0),
            image_url TEXT,
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            is_active INTEGER NOT NULL DEFAULT 1,
            is_featured INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO products (id, name_en, price_cents, image_url, stock)
        VALUES ('legacy-product', 'Legacy', 1000, '/static/products/legacy-product.webp', 1);
        """
    )
    conn.commit()
    conn.close()

    init_db(db_path)
    init_db(db_path)

    with get_db() as migrated:
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(products)")}
        images = migrated.execute(
            "SELECT product_id, image_url, thumbnail_url, is_primary FROM product_images"
        ).fetchall()

    assert "image_url" not in columns
    assert len(images) == 1
    assert images[0]["product_id"] == "legacy-product"
    assert images[0]["thumbnail_url"] == "/static/products/legacy-product_thumb.webp"
    assert images[0]["is_primary"] == 1
