"""Tests for image service and image upload route.

Covers: validation, processing, upload route, path traversal,
EXIF stripping, pixel flood, overwrite, directory auto-creation.
"""

import io

import pytest
from httpx import AsyncClient
from PIL import Image

from app.database import get_db
from app.services import object_storage_service
from app.services.image_service import (
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
    InvalidProductIdError,
    process_image,
    validate_image_file,
)

_R2_PUBLIC_BASE = "https://cdn.test.example"


class _FakeStorageBackend:
    """In-memory storage backend (key -> bytes) for tests; no live bucket."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)


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


def _open_variant(backend: _FakeStorageBackend, key: str) -> Image.Image:
    """Open a WebP variant stored in the fake backend under an R2 object key."""
    return Image.open(io.BytesIO(backend.objects[key]))


# --- Helpers ---


def _make_jpeg(width: int = 100, height: int = 100) -> bytes:
    """Create a minimal valid JPEG image in memory."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png(width: int = 100, height: int = 100) -> bytes:
    """Create a minimal valid PNG image in memory."""
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_with_exif() -> bytes:
    """Create a JPEG with EXIF metadata (Make, Model)."""
    img = Image.new("RGB", (100, 100), color=(0, 0, 255))
    from PIL.ExifTags import Base as ExifBase

    exif_data = img.getexif()
    exif_data[ExifBase.Make] = "TestCamera"
    exif_data[ExifBase.Model] = "TestModel"
    exif_data[ExifBase.Software] = "TestSoftware"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_data.tobytes())
    return buf.getvalue()


# --- Test validate_image_file ---


class TestValidateImageFile:
    """Task 56: validate_image_file tests."""

    def test_valid_jpeg_accepted(self):
        data = _make_jpeg()
        validate_image_file(data, "lavender-dream")  # Should not raise

    def test_valid_png_accepted(self):
        data = _make_png()
        validate_image_file(data, "midnight-amber")  # Should not raise

    def test_exactly_25mb_accepted(self):
        """File at exactly 25MB boundary is accepted."""
        # Create a JPEG header followed by padding up to exactly 25MB
        img_data = _make_jpeg()
        padded = img_data + b"\x00" * (25 * 1024 * 1024 - len(img_data))
        # This will pass size validation (magic bytes are valid)
        validate_image_file(padded, "test-product")

    def test_25mb_plus_one_byte_rejected(self):
        """File at 25MB + 1 byte is rejected."""
        img_data = _make_jpeg()
        oversized = img_data + b"\x00" * (25 * 1024 * 1024 - len(img_data) + 1)
        with pytest.raises(FileTooLargeError):
            validate_image_file(oversized, "test-product")

    def test_gif_magic_bytes_rejected(self):
        """GIF files (GIF89a magic) are rejected."""
        gif_data = b"GIF89a" + b"\x00" * 100
        with pytest.raises(InvalidImageTypeError):
            validate_image_file(gif_data, "test-product")

    def test_svg_text_rejected(self):
        """SVG (text) files are rejected."""
        svg_data = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with pytest.raises(InvalidImageTypeError):
            validate_image_file(svg_data, "test-product")

    def test_plain_text_rejected(self):
        """Plain text files are rejected."""
        text_data = b"Hello, this is not an image"
        with pytest.raises(InvalidImageTypeError):
            validate_image_file(text_data, "test-product")

    def test_empty_file_rejected(self):
        """Empty file is rejected (no magic bytes)."""
        with pytest.raises(InvalidImageTypeError):
            validate_image_file(b"", "test-product")


# --- Test process_image ---


class TestProcessImage:
    """Task 57: process_image tests."""

    def test_landscape_image_resized_within_bounds(self, fake_storage):
        """Landscape image is resized to fit within configured bounding boxes."""
        img_data = _make_jpeg(6000, 4000)
        result = process_image(img_data, "landscape-candle")

        assert result["image_url"] == f"{_R2_PUBLIC_BASE}/products/landscape-candle.webp"
        assert result["thumbnail_url"] == f"{_R2_PUBLIC_BASE}/products/landscape-candle_thumb.webp"
        assert result["zoom_url"] == f"{_R2_PUBLIC_BASE}/products/landscape-candle_zoom.webp"

        # Verify main image dimensions from the uploaded object bytes.
        assert "products/landscape-candle.webp" in fake_storage.objects
        with _open_variant(fake_storage, "products/landscape-candle.webp") as img:
            assert img.size == (2000, 1333)
        with _open_variant(fake_storage, "products/landscape-candle_zoom.webp") as img:
            assert img.size == (3000, 2000)

    def test_portrait_image_resized(self, fake_storage):
        """Portrait image fits within bounding box."""
        img_data = _make_jpeg(3000, 6000)
        process_image(img_data, "portrait-candle")

        with _open_variant(fake_storage, "products/portrait-candle.webp") as img:
            assert img.size == (1250, 2500)
        with _open_variant(fake_storage, "products/portrait-candle_zoom.webp") as img:
            assert img.size == (1875, 3750)

    def test_small_image_no_upscale(self, fake_storage):
        """Small image is NOT upscaled (thumbnail mode)."""
        img_data = _make_jpeg(200, 150)
        process_image(img_data, "small-candle")

        with _open_variant(fake_storage, "products/small-candle.webp") as img:
            assert img.width == 200
            assert img.height == 150
        with _open_variant(fake_storage, "products/small-candle_thumb.webp") as img:
            assert img.width == 200
            assert img.height == 150
        with _open_variant(fake_storage, "products/small-candle_zoom.webp") as img:
            assert img.width == 200
            assert img.height == 150

    def test_output_is_webp_format(self, fake_storage):
        """Main, thumbnail, and zoom are saved as WebP."""
        img_data = _make_jpeg(800, 600)
        process_image(img_data, "webp-test")

        with _open_variant(fake_storage, "products/webp-test.webp") as img:
            assert img.format == "WEBP"
        with _open_variant(fake_storage, "products/webp-test_thumb.webp") as img:
            assert img.format == "WEBP"
        with _open_variant(fake_storage, "products/webp-test_zoom.webp") as img:
            assert img.format == "WEBP"

    def test_main_thumb_and_zoom_created(self, fake_storage):
        """Main, thumbnail, and zoom objects are uploaded."""
        img_data = _make_jpeg(800, 600)
        process_image(img_data, "both-test")

        assert "products/both-test.webp" in fake_storage.objects
        assert "products/both-test_thumb.webp" in fake_storage.objects
        assert "products/both-test_zoom.webp" in fake_storage.objects

    def test_thumbnail_smaller_than_main(self, fake_storage):
        """Thumbnail dimensions are within 400x500."""
        img_data = _make_jpeg(2000, 2000)
        process_image(img_data, "thumb-size-test")

        with _open_variant(fake_storage, "products/thumb-size-test_thumb.webp") as img:
            assert img.width <= 400
            assert img.height <= 500

    def test_falls_back_to_local_static_files_when_r2_is_unconfigured(self, tmp_path):
        from app.config import get_settings

        settings = get_settings()
        original_static_path = settings.static_file_path
        original_base = settings.r2_public_base_url
        object_storage_service.set_backend(None)
        settings.static_file_path = str(tmp_path / "static")
        settings.r2_public_base_url = ""

        try:
            result = process_image(_make_jpeg(800, 600), "local-dev-image")
        finally:
            settings.static_file_path = original_static_path
            settings.r2_public_base_url = original_base

        assert result["image_url"] == "/static/products/local-dev-image.webp"
        assert result["thumbnail_url"] == "/static/products/local-dev-image_thumb.webp"
        assert result["zoom_url"] == "/static/products/local-dev-image_zoom.webp"
        assert (tmp_path / "static/products/local-dev-image.webp").exists()
        assert (tmp_path / "static/products/local-dev-image_thumb.webp").exists()
        assert (tmp_path / "static/products/local-dev-image_zoom.webp").exists()


class _FailOnNthPutBackend(_FakeStorageBackend):
    """Fake backend that raises on the Nth ``put_object`` (1-indexed).

    Used to exercise the partial-upload cleanup path: earlier variant objects
    must be deleted when a later variant upload fails.
    """

    def __init__(self, fail_on: int) -> None:
        super().__init__()
        self._fail_on = fail_on
        self._puts = 0

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._puts += 1
        if self._puts == self._fail_on:
            raise object_storage_service.MediaStorageError("boom")
        super().put_object(key, data, content_type)


class TestProcessImageOrphanCleanup:
    """A failed variant upload must not leave earlier variants orphaned."""

    @pytest.fixture()
    def _configure_base(self):
        from app.config import get_settings

        settings = get_settings()
        original_base = settings.r2_public_base_url
        settings.r2_public_base_url = _R2_PUBLIC_BASE
        try:
            yield
        finally:
            settings.r2_public_base_url = original_base

    @pytest.mark.parametrize("fail_on", [2, 3])
    def test_partial_upload_deletes_earlier_variants(self, _configure_base, fail_on):
        backend = _FailOnNthPutBackend(fail_on=fail_on)
        object_storage_service.set_backend(backend)
        try:
            with pytest.raises(object_storage_service.MediaStorageError):
                process_image(_make_jpeg(800, 600), "orphan-test")
        finally:
            object_storage_service.set_backend(None)

        # The variant that failed plus every earlier one must be gone: nothing
        # committed, nothing left behind.
        assert backend.objects == {}


# --- Test upload route ---


class TestImageUploadRoute:
    """Task 58: Upload route integration tests."""

    @pytest.fixture()
    def _product(self, db, app):
        """Seed a product for upload tests."""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
                "VALUES (%s, %s, %s, %s, 1)",
                ("test-candle-img", "Test Candle", 2500, 10),
            )

    @pytest.mark.asyncio
    async def test_upload_happy_path(self, admin_client: AsyncClient, _product, fake_storage, app):
        """Admin + valid image -> 201 with gallery image."""
        img_data = _make_jpeg(800, 600)

        response = await admin_client.post(
            "/v1/admin/products/test-candle-img/images",
            files={"file": ("image.jpg", img_data, "image/jpeg")},
        )

        assert response.status_code == 201
        body = response.json()
        assert "id" in body
        assert "image_url" in body
        assert "thumbnail_url" in body
        assert "zoom_url" in body
        assert body["image_url"].startswith(f"{_R2_PUBLIC_BASE}/products/test-candle-img_")
        assert body["zoom_url"].startswith(f"{_R2_PUBLIC_BASE}/products/test-candle-img_")
        assert body["is_primary"] is True

    @pytest.mark.asyncio
    async def test_upload_non_admin_rejected(self, client: AsyncClient, _product):
        """Non-admin → 401."""
        img_data = _make_jpeg()
        response = await client.post(
            "/v1/admin/products/test-candle-img/images",
            files={"file": ("image.jpg", img_data, "image/jpeg")},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_product_not_found(self, admin_client: AsyncClient):
        """Product doesn't exist → 404."""
        img_data = _make_jpeg()
        response = await admin_client.post(
            "/v1/admin/products/nonexistent-product/images",
            files={"file": ("image.jpg", img_data, "image/jpeg")},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, admin_client: AsyncClient, _product):
        """Non-image file → 422."""
        response = await admin_client.post(
            "/v1/admin/products/test-candle-img/images",
            files={"file": ("file.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_image_type"

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, admin_client: AsyncClient, _product):
        """>25MB file → 422."""
        oversized = b"\xff\xd8\xff" + b"\x00" * (25 * 1024 * 1024 + 1)
        response = await admin_client.post(
            "/v1/admin/products/test-candle-img/images",
            files={"file": ("big.jpg", oversized, "image/jpeg")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "file_too_large"
        assert "25MB" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_upload_inserts_product_image_row(
        self, admin_client: AsyncClient, _product, fake_storage, app
    ):
        """After upload, a product_images row is inserted."""
        img_data = _make_jpeg(800, 600)

        await admin_client.post(
            "/v1/admin/products/test-candle-img/images",
            files={"file": ("image.jpg", img_data, "image/jpeg")},
        )

        with get_db() as conn:
            row = conn.execute(
                (
                    "SELECT image_url, thumbnail_url, zoom_url, is_primary "
                    "FROM product_images WHERE product_id = %s"
                ),
                ("test-candle-img",),
            ).fetchone()
        assert row["image_url"].startswith(f"{_R2_PUBLIC_BASE}/products/test-candle-img_")
        assert row["thumbnail_url"].startswith(f"{_R2_PUBLIC_BASE}/products/test-candle-img_")
        assert row["zoom_url"].startswith(f"{_R2_PUBLIC_BASE}/products/test-candle-img_")
        assert row["is_primary"] == 1


class TestImageImportRoute:
    """Register pre-generated image variants without re-uploading the source file."""

    @pytest.fixture()
    def _product(self, db, app):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
                "VALUES (%s, %s, %s, %s, 1)",
                ("test-candle-import", "Test Candle", 2500, 10),
            )

    @pytest.mark.asyncio
    async def test_import_happy_path(self, admin_client: AsyncClient, _product):
        response = await admin_client.post(
            "/v1/admin/products/test-candle-import/images/import",
            json={
                "image_url": "/static/products/imported-main.webp",
                "thumbnail_url": "/static/products/imported-thumb.webp",
                "zoom_url": "/static/products/imported-zoom.webp",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["image_url"] == "/static/products/imported-main.webp"
        assert body["thumbnail_url"] == "/static/products/imported-thumb.webp"
        assert body["zoom_url"] == "/static/products/imported-zoom.webp"
        assert body["is_primary"] is True

    @pytest.mark.asyncio
    async def test_import_product_not_found(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/v1/admin/products/nonexistent-product/images/import",
            json={
                "image_url": "/static/products/imported-main.webp",
                "thumbnail_url": "/static/products/imported-thumb.webp",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_import_invalid_url(self, admin_client: AsyncClient, _product):
        response = await admin_client.post(
            "/v1/admin/products/test-candle-import/images/import",
            json={
                "image_url": "relative/path.webp",
                "thumbnail_url": "/static/products/imported-thumb.webp",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_import_inserts_product_image_row(self, admin_client: AsyncClient, _product):
        await admin_client.post(
            "/v1/admin/products/test-candle-import/images/import",
            json={
                "image_url": "/static/products/imported-main.webp",
                "thumbnail_url": "/static/products/imported-thumb.webp",
                "zoom_url": "/static/products/imported-zoom.webp",
            },
        )

        with get_db() as conn:
            row = conn.execute(
                (
                    "SELECT image_url, thumbnail_url, zoom_url, is_primary "
                    "FROM product_images WHERE product_id = %s"
                ),
                ("test-candle-import",),
            ).fetchone()
        assert row["image_url"] == "/static/products/imported-main.webp"
        assert row["thumbnail_url"] == "/static/products/imported-thumb.webp"
        assert row["zoom_url"] == "/static/products/imported-zoom.webp"
        assert row["is_primary"] == 1


# --- Test overwrite ---


class TestImageOverwrite:
    """Task 59: Upload twice, second replaces first."""

    def test_overwrite_replaces_existing(self, fake_storage):
        """Second upload overwrites the first."""
        img1 = _make_jpeg(100, 100)
        img2 = _make_png(200, 200)

        result1 = process_image(img1, "overwrite-test")
        result2 = process_image(img2, "overwrite-test")

        # Both return same URLs
        assert result1["image_url"] == result2["image_url"]

        # Object contains the second image (200x200, not 100x100)
        with _open_variant(fake_storage, "products/overwrite-test.webp") as img:
            assert img.width == 200
            assert img.height == 200

    def test_image_id_creates_distinct_files(self, fake_storage):
        """Supplying image_id appends instead of overwriting."""
        img1 = _make_jpeg(100, 100)
        img2 = _make_png(200, 200)
        id1 = "a" * 32
        id2 = "b" * 32

        result1 = process_image(img1, "gallery-test", image_id=id1)
        result2 = process_image(img2, "gallery-test", image_id=id2)

        assert result1["image_url"] != result2["image_url"]
        assert f"products/gallery-test_{id1}.webp" in fake_storage.objects
        assert f"products/gallery-test_{id2}.webp" in fake_storage.objects
        assert f"products/gallery-test_{id1}_zoom.webp" in fake_storage.objects
        assert f"products/gallery-test_{id2}_zoom.webp" in fake_storage.objects


# --- Test directory auto-creation ---


class TestDirectoryAutoCreation:
    """Task 60: objects uploaded to R2 (no local disk dependency)."""

    def test_products_objects_uploaded(self, fake_storage):
        """Process uploads variant objects under the products/ prefix."""
        img_data = _make_jpeg(100, 100)

        process_image(img_data, "auto-dir-test")

        assert "products/auto-dir-test.webp" in fake_storage.objects


# --- Test corrupted image ---


class TestCorruptedImage:
    """Task 61: Corrupted image handled gracefully."""

    def test_valid_magic_bytes_but_truncated_body(self):
        """JPEG magic bytes but truncated → ImageProcessingError, not crash."""
        # Valid JPEG header but no actual image data
        truncated = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        validate_image_file(truncated, "corrupted-test")  # Passes validation

        with pytest.raises(ImageProcessingError):
            process_image(truncated, "corrupted-test")


# --- Test pixel flood ---


class TestPixelFlood:
    """Task 62: Pixel flood protection."""

    def test_exactly_25m_pixels_accepted(self, fake_storage):
        """5000×5000 = 25M pixels → accepted."""
        # Create a very large but valid JPEG
        img = Image.new("RGB", (5000, 5000), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_data = buf.getvalue()

        # Should not raise
        result = process_image(img_data, "large-ok")
        assert "image_url" in result
        assert "zoom_url" in result

    def test_over_25m_pixels_rejected(self):
        """5001×5000 > 25M pixels → rejected."""
        # Temporarily increase MAX_IMAGE_PIXELS to create the test image. Use
        # try/finally so a failure mid-creation cannot leave the global disabled
        # for the rest of this xdist worker (which would silently defeat the
        # decompression-bomb guard in every subsequent test).
        old_max = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = None  # Disable for creation
        try:
            img = Image.new("RGB", (5001, 5000), color=(128, 128, 128))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            img_data = buf.getvalue()
        finally:
            Image.MAX_IMAGE_PIXELS = old_max  # Restore for processing

        with pytest.raises(ImageProcessingError, match="image_dimensions_too_large"):
            process_image(img_data, "too-large")


# --- Test path traversal prevention ---


class TestPathTraversal:
    """Task 63: Path traversal prevention."""

    def test_product_id_with_dot_dot_slash_rejected(self):
        """product_id containing ../ is rejected by slug validation."""
        with pytest.raises(InvalidProductIdError):
            validate_image_file(b"\xff\xd8\xff" + b"\x00" * 100, "../escape")

    def test_product_id_with_null_byte_rejected(self):
        """product_id with null byte rejected."""
        with pytest.raises(InvalidProductIdError):
            validate_image_file(b"\xff\xd8\xff" + b"\x00" * 100, "test\x00evil")

    def test_product_id_with_backslash_rejected(self):
        """product_id with backslash rejected."""
        with pytest.raises(InvalidProductIdError):
            validate_image_file(b"\xff\xd8\xff" + b"\x00" * 100, "test\\evil")

    def test_product_id_url_encoded_dots_rejected(self):
        """product_id with URL-encoded traversal rejected."""
        with pytest.raises(InvalidProductIdError):
            validate_image_file(b"\xff\xd8\xff" + b"\x00" * 100, "%2e%2e%2f")


# --- Test EXIF stripping ---


class TestExifStripping:
    """Task 64: EXIF data stripped from output."""

    def test_output_has_no_exif(self, fake_storage):
        """Upload JPEG with EXIF, verify output WebP has no EXIF."""
        img_data = _make_jpeg_with_exif()
        process_image(img_data, "exif-test")

        with _open_variant(fake_storage, "products/exif-test.webp") as img:
            exif = img.getexif()
            # WebP output should have no EXIF data
            assert len(exif) == 0


# --- Test product_id slug validation ---


class TestProductIdSlugValidation:
    """Task 65: Non-slug product_id rejected."""

    def test_spaces_rejected(self):
        with pytest.raises(InvalidProductIdError):
            validate_image_file(_make_jpeg(), "has spaces")

    def test_uppercase_rejected(self):
        with pytest.raises(InvalidProductIdError):
            validate_image_file(_make_jpeg(), "HasUppercase")

    def test_special_chars_rejected(self):
        with pytest.raises(InvalidProductIdError):
            validate_image_file(_make_jpeg(), "has@special!")

    def test_single_char_rejected(self):
        """Single character doesn't match regex (needs at least 2 chars)."""
        with pytest.raises(InvalidProductIdError):
            validate_image_file(_make_jpeg(), "a")

    def test_valid_slug_accepted(self):
        """Valid slugs pass validation."""
        validate_image_file(_make_jpeg(), "valid-slug-123")
        validate_image_file(_make_jpeg(), "ab")
        validate_image_file(_make_jpeg(), "lavender-dream-300ml")


def _make_jpeg_with_orientation(width: int, height: int, orientation: int) -> bytes:
    """Create a JPEG whose EXIF orientation flag requests a rotation.

    Orientation 6 means "rotate 90° CW for display", so the stored pixels are
    landscape while the intended display is portrait.
    """
    img = Image.new("RGB", (width, height), color=(10, 20, 30))
    from PIL.ExifTags import Base as ExifBase

    exif_data = img.getexif()
    exif_data[ExifBase.Orientation] = orientation
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_data.tobytes())
    return buf.getvalue()


class TestExifOrientationApplied:
    """EXIF orientation is baked into the pixels before resizing (upright output)."""

    def test_orientation_6_uprights_portrait_photo(self, fake_storage):
        # Stored 120x60 landscape, orientation 6 → display is 60x120 portrait.
        img_data = _make_jpeg_with_orientation(120, 60, orientation=6)
        process_image(img_data, "sideways-candle")

        with _open_variant(fake_storage, "products/sideways-candle.webp") as img:
            # After exif_transpose the image is uprighted: portrait, not landscape.
            assert img.width < img.height
            assert img.size == (60, 120)

    def test_no_orientation_flag_leaves_dimensions(self, fake_storage):
        # A plain image (editor canvas export carries no EXIF) is a no-op.
        img_data = _make_jpeg(120, 60)
        process_image(img_data, "plain-candle")

        with _open_variant(fake_storage, "products/plain-candle.webp") as img:
            assert img.size == (120, 60)


class TestQualityAndDimensionConstants:
    """Quality bump: main q92, zoom 3000x3750 q95; safety ceilings unchanged."""

    def test_output_constants(self):
        from app.services import image_service as svc

        assert svc._MAIN_QUALITY == 92
        assert svc._ZOOM_MAX_SIZE == (3000, 3750)
        assert svc._ZOOM_QUALITY == 95
        assert svc._THUMB_QUALITY == 80

    def test_zoom_box_under_pixel_ceiling(self):
        from app.services import image_service as svc

        zoom_pixels = svc._ZOOM_MAX_SIZE[0] * svc._ZOOM_MAX_SIZE[1]
        assert zoom_pixels <= svc.MAX_IMAGE_PIXELS

    def test_safety_limits_unchanged(self):
        from app.services import image_service as svc

        assert svc.MAX_IMAGE_PIXELS == 25_000_000
        assert svc.MAX_FILE_SIZE == 25 * 1024 * 1024
