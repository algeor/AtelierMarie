"""Service tests for admin-managed reusable site media."""

from io import BytesIO

import pytest
from PIL import Image

from app.database import get_db
from app.services import site_media_service


def _make_jpeg(width: int = 120, height: int = 90) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(180, 120, 120)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture()
def site_media_static_path(tmp_path, db):
    static_path = tmp_path / "static"
    from app.config import get_settings

    settings = get_settings()
    original_static_path = settings.static_file_path
    settings.static_file_path = str(static_path)
    yield static_path
    settings.static_file_path = original_static_path


def test_seeded_assets_include_defaults_and_public_urls(site_media_static_path):
    admin = site_media_service.list_admin_assets()["assets"]
    keys = [asset["key"] for asset in admin]

    assert "home_hero" in keys
    assert "page_background" in keys
    assert next(asset for asset in admin if asset["key"] == "home_hero")["effective_url"] is None
    assert (
        site_media_service.get_public_assets()["assets"]["page_background"]
        == "/rebrand/watercolor-page-bg.webp"
    )


def test_upload_and_clear_asset_image(site_media_static_path, fake_storage):
    uploaded = site_media_service.set_asset_image("home_hero", _make_jpeg())

    assert uploaded["image_id"]
    assert uploaded["image_url"].startswith(
        "https://cdn.test.example/products/site-media-home-hero_"
    )
    assert site_media_service.get_public_assets()["assets"]["home_hero"] == uploaded["image_url"]

    with get_db() as conn:
        row = conn.execute(
            "SELECT image_url, thumbnail_url, zoom_url FROM site_media_assets "
            "WHERE key = 'home_hero'"
        ).fetchone()
    assert row["image_url"] == uploaded["image_url"]

    cleared = site_media_service.clear_asset_image("home_hero")
    assert cleared["image_id"] is None
    assert cleared["effective_url"] is None
    assert site_media_service.get_public_assets()["assets"]["home_hero"] is None


def test_upload_asset_image_falls_back_to_local_static_when_r2_is_unconfigured(
    site_media_static_path,
):
    from app.config import get_settings
    from app.services import object_storage_service

    settings = get_settings()
    original_base = settings.r2_public_base_url
    settings.r2_public_base_url = ""
    object_storage_service.set_backend(None)

    try:
        uploaded = site_media_service.set_asset_image("home_hero", _make_jpeg())
    finally:
        settings.r2_public_base_url = original_base

    assert uploaded["image_url"].startswith("/static/products/site-media-home-hero_")
    assert uploaded["thumbnail_url"].startswith("/static/products/site-media-home-hero_")
    assert uploaded["zoom_url"].startswith("/static/products/site-media-home-hero_")
    assert site_media_static_path.joinpath(
        "products", uploaded["image_url"].rsplit("/", 1)[-1]
    ).exists()


def test_unknown_asset_key_is_rejected(site_media_static_path):
    with pytest.raises(site_media_service.SiteMediaNotFoundError):
        site_media_service.set_asset_image("missing", _make_jpeg())
