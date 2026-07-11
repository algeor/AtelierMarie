"""Tests for image service and image upload route.

Covers: validation, processing, upload route, path traversal,
EXIF stripping, pixel flood, overwrite, directory auto-creation.
"""

import io
import sqlite3
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

from app.services.image_service import (
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
    InvalidProductIdError,
    process_image,
    validate_image_file,
)

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

    def test_exactly_5mb_accepted(self):
        """File at exactly 5MB boundary is accepted."""
        # Create a JPEG header followed by padding up to exactly 5MB
        img_data = _make_jpeg()
        # Pad to exactly 5MB
        padded = img_data + b"\x00" * (5 * 1024 * 1024 - len(img_data))
        # This will pass size validation (magic bytes are valid)
        validate_image_file(padded, "test-product")

    def test_5mb_plus_one_byte_rejected(self):
        """File at 5MB + 1 byte is rejected."""
        img_data = _make_jpeg()
        oversized = img_data + b"\x00" * (5 * 1024 * 1024 - len(img_data) + 1)
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

    def test_landscape_image_resized_within_bounds(self, tmp_path):
        """Landscape image is resized to fit within 1200x1500 bounding box."""
        img_data = _make_jpeg(2400, 1600)
        result = process_image(img_data, "landscape-candle", str(tmp_path))

        assert result["image_url"] == "/static/products/landscape-candle.webp"
        assert result["thumbnail_url"] == "/static/products/landscape-candle_thumb.webp"

        # Verify main image dimensions
        main_path = tmp_path / "products" / "landscape-candle.webp"
        assert main_path.exists()
        with Image.open(main_path) as img:
            assert img.width <= 1200
            assert img.height <= 1500

    def test_portrait_image_resized(self, tmp_path):
        """Portrait image fits within bounding box."""
        img_data = _make_jpeg(1000, 3000)
        process_image(img_data, "portrait-candle", str(tmp_path))

        main_path = tmp_path / "products" / "portrait-candle.webp"
        with Image.open(main_path) as img:
            assert img.width <= 1200
            assert img.height <= 1500

    def test_small_image_no_upscale(self, tmp_path):
        """Small image is NOT upscaled (thumbnail mode)."""
        img_data = _make_jpeg(200, 150)
        process_image(img_data, "small-candle", str(tmp_path))

        main_path = tmp_path / "products" / "small-candle.webp"
        with Image.open(main_path) as img:
            assert img.width == 200
            assert img.height == 150

    def test_output_is_webp_format(self, tmp_path):
        """Both main and thumbnail are saved as WebP."""
        img_data = _make_jpeg(800, 600)
        process_image(img_data, "webp-test", str(tmp_path))

        main_path = tmp_path / "products" / "webp-test.webp"
        thumb_path = tmp_path / "products" / "webp-test_thumb.webp"

        with Image.open(main_path) as img:
            assert img.format == "WEBP"
        with Image.open(thumb_path) as img:
            assert img.format == "WEBP"

    def test_both_main_and_thumb_created(self, tmp_path):
        """Both main and thumbnail files are created."""
        img_data = _make_jpeg(800, 600)
        process_image(img_data, "both-test", str(tmp_path))

        assert (tmp_path / "products" / "both-test.webp").exists()
        assert (tmp_path / "products" / "both-test_thumb.webp").exists()

    def test_thumbnail_smaller_than_main(self, tmp_path):
        """Thumbnail dimensions are within 400x500."""
        img_data = _make_jpeg(2000, 2000)
        process_image(img_data, "thumb-size-test", str(tmp_path))

        thumb_path = tmp_path / "products" / "thumb-size-test_thumb.webp"
        with Image.open(thumb_path) as img:
            assert img.width <= 400
            assert img.height <= 500


# --- Test upload route ---


class TestImageUploadRoute:
    """Task 58: Upload route integration tests."""

    @pytest.fixture()
    def _product(self, db_path, app):
        """Seed a product for upload tests."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            ("test-candle-img", "Test Candle", 2500, 10),
        )
        conn.commit()
        conn.close()

    @pytest.mark.asyncio
    async def test_upload_happy_path(self, admin_client: AsyncClient, _product, tmp_path, app):
        """Admin + valid image → 200 with URLs."""
        img_data = _make_jpeg(800, 600)

        # Patch static path to use tmp_path
        from app.config import get_settings

        settings = get_settings()
        original = settings.static_file_path
        settings.static_file_path = str(tmp_path)
        try:
            response = await admin_client.post(
                "/v1/admin/products/test-candle-img/image",
                files={"file": ("image.jpg", img_data, "image/jpeg")},
            )
        finally:
            settings.static_file_path = original

        assert response.status_code == 200
        body = response.json()
        assert "image_url" in body
        assert "thumbnail_url" in body
        assert body["image_url"] == "/static/products/test-candle-img.webp"

    @pytest.mark.asyncio
    async def test_upload_non_admin_rejected(self, client: AsyncClient, _product):
        """Non-admin → 401."""
        img_data = _make_jpeg()
        response = await client.post(
            "/v1/admin/products/test-candle-img/image",
            files={"file": ("image.jpg", img_data, "image/jpeg")},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_product_not_found(self, admin_client: AsyncClient):
        """Product doesn't exist → 404."""
        img_data = _make_jpeg()
        response = await admin_client.post(
            "/v1/admin/products/nonexistent-product/image",
            files={"file": ("image.jpg", img_data, "image/jpeg")},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, admin_client: AsyncClient, _product):
        """Non-image file → 422."""
        response = await admin_client.post(
            "/v1/admin/products/test-candle-img/image",
            files={"file": ("file.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_image_type"

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, admin_client: AsyncClient, _product):
        """6MB file → 422."""
        oversized = b"\xff\xd8\xff" + b"\x00" * (6 * 1024 * 1024)
        response = await admin_client.post(
            "/v1/admin/products/test-candle-img/image",
            files={"file": ("big.jpg", oversized, "image/jpeg")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "file_too_large"

    @pytest.mark.asyncio
    async def test_upload_updates_db_image_url(
        self, admin_client: AsyncClient, _product, db_path, tmp_path, app
    ):
        """After upload, product.image_url is updated in DB."""
        img_data = _make_jpeg(800, 600)

        from app.config import get_settings

        settings = get_settings()
        original = settings.static_file_path
        settings.static_file_path = str(tmp_path)
        try:
            await admin_client.post(
                "/v1/admin/products/test-candle-img/image",
                files={"file": ("image.jpg", img_data, "image/jpeg")},
            )
        finally:
            settings.static_file_path = original

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT image_url FROM products WHERE id = ?", ("test-candle-img",)
        ).fetchone()
        conn.close()
        assert row["image_url"] == "/static/products/test-candle-img.webp"


# --- Test overwrite ---


class TestImageOverwrite:
    """Task 59: Upload twice, second replaces first."""

    def test_overwrite_replaces_existing(self, tmp_path):
        """Second upload overwrites the first."""
        img1 = _make_jpeg(100, 100)
        img2 = _make_png(200, 200)

        result1 = process_image(img1, "overwrite-test", str(tmp_path))
        result2 = process_image(img2, "overwrite-test", str(tmp_path))

        # Both return same URLs
        assert result1["image_url"] == result2["image_url"]

        # File contains the second image (200x200, not 100x100)
        main_path = tmp_path / "products" / "overwrite-test.webp"
        with Image.open(main_path) as img:
            assert img.width == 200
            assert img.height == 200


# --- Test directory auto-creation ---


class TestDirectoryAutoCreation:
    """Task 60: Directory created on first upload."""

    def test_products_dir_created_if_missing(self, tmp_path):
        """Process creates products/ subdirectory if it doesn't exist."""
        # Use a nested non-existent path
        static_path = str(tmp_path / "new_static")
        img_data = _make_jpeg(100, 100)

        process_image(img_data, "auto-dir-test", static_path)

        assert (Path(static_path) / "products" / "auto-dir-test.webp").exists()


# --- Test corrupted image ---


class TestCorruptedImage:
    """Task 61: Corrupted image handled gracefully."""

    def test_valid_magic_bytes_but_truncated_body(self, tmp_path):
        """JPEG magic bytes but truncated → ImageProcessingError, not crash."""
        # Valid JPEG header but no actual image data
        truncated = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        validate_image_file(truncated, "corrupted-test")  # Passes validation

        with pytest.raises(ImageProcessingError):
            process_image(truncated, "corrupted-test", str(tmp_path))


# --- Test pixel flood ---


class TestPixelFlood:
    """Task 62: Pixel flood protection."""

    def test_exactly_25m_pixels_accepted(self, tmp_path):
        """5000×5000 = 25M pixels → accepted."""
        # Create a very large but valid JPEG
        img = Image.new("RGB", (5000, 5000), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_data = buf.getvalue()

        # Should not raise
        result = process_image(img_data, "large-ok", str(tmp_path))
        assert "image_url" in result

    def test_over_25m_pixels_rejected(self, tmp_path):
        """5001×5000 > 25M pixels → rejected."""
        # Temporarily increase MAX_IMAGE_PIXELS to create the test image
        old_max = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = None  # Disable for creation
        img = Image.new("RGB", (5001, 5000), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_data = buf.getvalue()
        Image.MAX_IMAGE_PIXELS = old_max  # Restore for processing

        with pytest.raises(ImageProcessingError, match="image_dimensions_too_large"):
            process_image(img_data, "too-large", str(tmp_path))


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

    def test_output_has_no_exif(self, tmp_path):
        """Upload JPEG with EXIF, verify output WebP has no EXIF."""
        img_data = _make_jpeg_with_exif()
        process_image(img_data, "exif-test", str(tmp_path))

        main_path = tmp_path / "products" / "exif-test.webp"
        with Image.open(main_path) as img:
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
