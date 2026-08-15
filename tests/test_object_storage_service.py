"""Tests for the object storage service (fake in-memory backend — no live R2)."""

import pytest

from app.config import get_settings
from app.services import object_storage_service as oss


class FakeBackend:
    """In-memory storage backend (key->bytes) for tests."""

    def __init__(self, *, fail: bool = False) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.deleted: list[str] = []
        self.fail = fail

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        if self.fail:
            raise oss.MediaStorageError("boom")
        self.objects[key] = (data, content_type)

    def delete_object(self, key: str) -> None:
        if self.fail:
            raise oss.MediaStorageError("boom")
        self.deleted.append(key)
        self.objects.pop(key, None)


@pytest.fixture(autouse=True)
def _r2_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("R2_BUCKET", "test-bucket")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://accountid.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://media.example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_backend():
    backend = FakeBackend()
    oss.set_backend(backend)
    yield backend
    oss.set_backend(None)


# --- Key derivation + slug allowlist -------------------------------------------


def test_image_variant_keys_share_stem():
    assert oss.object_key_for_image("lavender-dream-300ml", "ab12") == (
        "products/lavender-dream-300ml_ab12.webp"
    )
    assert oss.object_key_for_image_thumb("lavender-dream-300ml", "ab12") == (
        "products/lavender-dream-300ml_ab12_thumb.webp"
    )
    assert oss.object_key_for_image_zoom("lavender-dream-300ml", "ab12") == (
        "products/lavender-dream-300ml_ab12_zoom.webp"
    )


def test_video_keys():
    assert oss.object_key_for_video("candle-01", "v9") == "products/candle-01_v9_video.mp4"
    assert oss.object_key_for_video_poster("candle-01", "v9") == (
        "products/candle-01_v9_poster.webp"
    )


@pytest.mark.parametrize(
    "bad_product_id",
    ["../etc", "foo/bar", "foo\\bar", "UPPER", "-leading", "trailing-", "a b", "", ".."],
)
def test_slug_allowlist_rejects_bad_product_id(bad_product_id: str):
    with pytest.raises(oss.MediaStorageError):
        oss.object_key_for_image(bad_product_id, "ab12")


def test_object_key_for_stem_rejects_traversal():
    with pytest.raises(oss.MediaStorageError):
        oss.object_key_for_stem("../evil", ".webp")


def test_object_key_for_stem_reuses_stem():
    assert oss.object_key_for_stem("prod_img1", "_thumb.webp") == "products/prod_img1_thumb.webp"


# --- Public URL join -----------------------------------------------------------


def test_public_url_joins_base_and_key():
    assert oss.public_url("products/lavender-dream-300ml_ab12.webp") == (
        "https://media.example.com/products/lavender-dream-300ml_ab12.webp"
    )


def test_public_url_normalizes_trailing_slash(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://media.example.com/")
    get_settings.cache_clear()
    assert oss.public_url("products/x.webp") == "https://media.example.com/products/x.webp"


# --- Upload / delete against fake backend --------------------------------------


def test_upload_bytes_stores_and_returns_public_url(fake_backend: FakeBackend):
    key = oss.object_key_for_image("candle-01", "img1")
    url = oss.upload_bytes(key, b"webpdata", "image/webp")
    assert url == "https://media.example.com/products/candle-01_img1.webp"
    assert fake_backend.objects[key] == (b"webpdata", "image/webp")


def test_delete_object_is_idempotent(fake_backend: FakeBackend):
    key = "products/candle-01_img1.webp"
    # Deleting a key that was never stored succeeds (best-effort / idempotent).
    oss.delete_object(key)
    oss.upload_bytes(key, b"x", "image/webp")
    oss.delete_object(key)
    oss.delete_object(key)  # again, still fine
    assert key not in fake_backend.objects


# --- Error wrapping ------------------------------------------------------------


def test_upload_wraps_backend_error():
    oss.set_backend(FakeBackend(fail=True))
    try:
        with pytest.raises(oss.MediaStorageError):
            oss.upload_bytes("products/x.webp", b"x", "image/webp")
    finally:
        oss.set_backend(None)


def test_botocore_error_wrapped_as_media_storage_error(monkeypatch: pytest.MonkeyPatch):
    """The real R2 backend must wrap botocore exceptions, never leak them."""
    from botocore.exceptions import EndpointConnectionError

    oss.set_backend(None)

    class _RaisingClient:
        def put_object(self, **_kwargs):
            raise EndpointConnectionError(endpoint_url="https://r2")

        def delete_object(self, **_kwargs):
            raise EndpointConnectionError(endpoint_url="https://r2")

    backend = oss._R2Backend.__new__(oss._R2Backend)
    backend._bucket = "test-bucket"
    backend._client = _RaisingClient()

    with pytest.raises(oss.MediaStorageError):
        backend.put_object("products/x.webp", b"x", "image/webp")
    with pytest.raises(oss.MediaStorageError):
        backend.delete_object("products/x.webp")


def test_write_path_raises_config_error_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("R2_BUCKET", "")
    monkeypatch.setenv("R2_ENDPOINT_URL", "")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "")
    get_settings.cache_clear()
    oss.set_backend(None)
    try:
        with pytest.raises(oss.StorageConfigError):
            oss.upload_bytes("products/x.webp", b"x", "image/webp")
    finally:
        oss.set_backend(None)
        get_settings.cache_clear()
