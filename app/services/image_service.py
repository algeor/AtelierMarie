"""Image service — validation, processing, and storage for product images.

Handles magic-byte validation, Pillow-based resize/conversion, EXIF stripping,
and object-key traversal prevention. All processed images are stored as WebP
objects in R2 via :mod:`app.services.object_storage_service`; this module
performs no local disk writes.
"""

import io
import re
import warnings

import structlog
from PIL import Image, ImageOps

from app.services import object_storage_service

logger = structlog.get_logger(__name__)


# Pixel flood protection — set at MODULE LEVEL before any image processing
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Output dimensions (max bounding box, aspect ratio preserved)
_MAIN_MAX_SIZE = (2000, 2500)
_THUMB_MAX_SIZE = (400, 500)
_ZOOM_MAX_SIZE = (3000, 3750)  # 11.25 MP — enough pixels to pan into fine detail
_MAIN_QUALITY = 92
_THUMB_QUALITY = 80
_ZOOM_QUALITY = 95
_RESAMPLE_LANCZOS = Image.Resampling.LANCZOS

# File size limit
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

# Valid magic bytes
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89\x50\x4e\x47"

# Product ID slug format
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
_IMAGE_ID_RE = re.compile(r"^[a-f0-9]{32}$")

# WebP object content type for R2 uploads.
_WEBP_CONTENT_TYPE = "image/webp"


# --- Exceptions ---


class ImageServiceError(Exception):
    """Base for all image service errors."""


class InvalidImageTypeError(ImageServiceError):
    """File is not a supported image type (JPEG or PNG)."""


class FileTooLargeError(ImageServiceError):
    """File exceeds the maximum allowed size."""


class ImageProcessingError(ImageServiceError):
    """Image could not be processed (corrupted, too large dimensions, etc.)."""


class InvalidProductIdError(ImageServiceError):
    """Product ID does not match the required slug format."""


class InvalidImageIdError(ImageServiceError):
    """Image ID does not match the required UUID hex format."""


# --- Public Functions ---


def validate_image_file(file_bytes: bytes, product_id: str) -> None:
    """Validate image file bytes and product_id slug format.

    Checks:
        - product_id matches slug pattern
        - File size ≤ 25MB
        - Magic bytes indicate JPEG or PNG

    Raises:
        InvalidProductIdError: If product_id is not a valid slug.
        FileTooLargeError: If file exceeds 25MB.
        InvalidImageTypeError: If magic bytes don't match JPEG or PNG.
    """
    # Validate product_id slug format first (before any object-key construction)
    if not product_id or not _SLUG_RE.match(product_id):
        raise InvalidProductIdError(
            f"Product ID must match slug format (lowercase alphanumeric + hyphens): {product_id!r}"
        )

    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise FileTooLargeError(
            f"File size {len(file_bytes)} bytes exceeds maximum of {MAX_FILE_SIZE} bytes (25MB)"
        )

    # Check magic bytes
    if not (file_bytes[:3] == _JPEG_MAGIC or file_bytes[:4] == _PNG_MAGIC):
        raise InvalidImageTypeError("Unsupported image format. Only JPEG and PNG are accepted.")


def validate_image_id(image_id: str) -> None:
    """Validate the per-image UUID hex used in object keys."""
    if not image_id or not _IMAGE_ID_RE.match(image_id):
        raise InvalidImageIdError(f"Image ID must be a UUID hex string: {image_id!r}")


def _encode_webp(img: Image.Image, max_size: tuple[int, int], quality: int) -> bytes:
    """Return WebP-encoded bytes of a bounded, downscaled copy of ``img``."""
    variant = img.copy()
    variant.thumbnail(max_size, _RESAMPLE_LANCZOS)
    buffer = io.BytesIO()
    variant.save(buffer, format="WEBP", quality=quality)
    return buffer.getvalue()


def process_image(
    file_bytes: bytes,
    product_id: str,
    static_path: str | None = None,  # noqa: ARG001 - retained for signature compat; unused post-R2
    image_id: str | None = None,
) -> dict:
    """Process an image: validate with Pillow, strip EXIF, resize, save as WebP.

    Creates main, thumbnail, and zoom derivatives and uploads each to R2 with
    ``ContentType: image/webp``. Uploads happen before any DB write by the
    caller, so a failed upload leaves no dangling row.

    Args:
        file_bytes: Raw file bytes (already validated by validate_image_file).
        product_id: Product slug (already validated).
        static_path: Deprecated/unused. Retained only for call-site
            compatibility during the R2 migration; media no longer touches disk.
        image_id: Optional UUID hex. When supplied, keys are unique per image.

    Returns:
        Dict with image_url, thumbnail_url, and zoom_url — absolute R2 public URLs.

    Raises:
        ImageProcessingError: If the image is corrupted or dimensions exceed limits.
        object_storage_service.MediaStorageError: If an R2 upload fails or R2 is
            unconfigured.
    """
    # Defensive validation for direct service callers. The upload route also
    # validates before use, but this function derives object keys too.
    if not product_id or not _SLUG_RE.match(product_id):
        raise InvalidProductIdError(
            f"Product ID must match slug format (lowercase alphanumeric + hyphens): {product_id!r}"
        )
    if image_id is not None:
        validate_image_id(image_id)

    filename_stem = f"{product_id}_{image_id}" if image_id else product_id

    # Derive object keys up front. The stem-based helper re-validates that the
    # derived key stays under the products/ prefix (traversal guard).
    main_key = object_storage_service.object_key_for_stem(filename_stem, ".webp")
    thumb_key = object_storage_service.object_key_for_stem(filename_stem, "_thumb.webp")
    zoom_key = object_storage_service.object_key_for_stem(filename_stem, "_zoom.webp")

    # Open and verify with Pillow
    try:
        img: Image.Image = Image.open(io.BytesIO(file_bytes))
        img.verify()  # Verify it's a valid image (doesn't load pixel data)

        # Re-open after verify (verify() leaves the file in an unusable state)
        img = Image.open(io.BytesIO(file_bytes))

        # Explicit pixel count check (Pillow only raises DecompressionBombError
        # at 2x the limit; we reject at 1x)
        width, height = img.size
        if width * height > MAX_IMAGE_PIXELS:
            raise ImageProcessingError("image_dimensions_too_large")

        # Suppress DecompressionBombWarning for images at the boundary
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            img.load()  # Force full decode to catch truncated files
    except ImageProcessingError:
        raise
    except Image.DecompressionBombError as e:
        raise ImageProcessingError("image_dimensions_too_large") from e
    except Exception as e:
        raise ImageProcessingError(f"Image file is corrupted or cannot be processed: {e}") from e

    # Apply EXIF orientation to the pixels BEFORE resizing, then continue.
    # WebP output below carries no metadata, so the orientation flag would
    # otherwise be lost without rotating the pixels — leaving phone photos
    # sideways. exif_transpose bakes the correct orientation into the pixels;
    # for images with no EXIF (e.g. canvas exports from the admin editor) it is
    # a no-op.
    img = ImageOps.exif_transpose(img)

    # Convert to RGB if necessary (handles RGBA, P, L modes)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        # Create white background for transparent images
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background

    # Encode all three WebP variants in memory (no disk writes).
    main_bytes = _encode_webp(img, _MAIN_MAX_SIZE, _MAIN_QUALITY)
    thumb_bytes = _encode_webp(img, _THUMB_MAX_SIZE, _THUMB_QUALITY)
    # The zoom derivative is still a bounded, EXIF-stripped re-encode — never
    # the byte-for-byte uploaded original.
    zoom_bytes = _encode_webp(img, _ZOOM_MAX_SIZE, _ZOOM_QUALITY)

    # Upload all variants to R2. Any botocore/config failure surfaces as a
    # MediaStorageError (raised by the storage service), so the caller does not
    # write a DB row referencing an object that failed to upload. The variants
    # are uploaded sequentially, so a failure on the 2nd/3rd upload would leave
    # the earlier objects orphaned in the bucket (no DB row references them).
    # Compensate by best-effort deleting the keys written so far before
    # re-raising, so a partial failure leaves nothing behind.
    uploaded_keys: list[str] = []
    try:
        image_url = object_storage_service.upload_bytes(main_key, main_bytes, _WEBP_CONTENT_TYPE)
        uploaded_keys.append(main_key)
        thumbnail_url = object_storage_service.upload_bytes(
            thumb_key, thumb_bytes, _WEBP_CONTENT_TYPE
        )
        uploaded_keys.append(thumb_key)
        zoom_url = object_storage_service.upload_bytes(zoom_key, zoom_bytes, _WEBP_CONTENT_TYPE)
    except object_storage_service.MediaStorageError:
        for key in uploaded_keys:
            try:
                object_storage_service.delete_object(key)
            except object_storage_service.MediaStorageError as cleanup_exc:
                logger.warning(
                    "image_upload_orphan_cleanup_failed", key=key, error=str(cleanup_exc)
                )
        raise

    return {
        "image_url": image_url,
        "thumbnail_url": thumbnail_url,
        "zoom_url": zoom_url,
    }
