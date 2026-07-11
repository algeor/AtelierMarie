"""Image service — validation, processing, and storage for product images.

Handles magic-byte validation, Pillow-based resize/conversion, EXIF stripping,
and path-traversal prevention. All images are stored as WebP.
"""

import re
from pathlib import Path

from PIL import Image

from app.config import get_settings

# Pixel flood protection — set at MODULE LEVEL before any image processing
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Output dimensions (max bounding box, aspect ratio preserved)
_MAIN_MAX_SIZE = (1200, 1500)
_THUMB_MAX_SIZE = (400, 500)
_MAIN_QUALITY = 85
_THUMB_QUALITY = 80

# File size limit
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Valid magic bytes
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89\x50\x4e\x47"

# Product ID slug format
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


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


# --- Public Functions ---


def validate_image_file(file_bytes: bytes, product_id: str) -> None:
    """Validate image file bytes and product_id slug format.

    Checks:
        - product_id matches slug pattern
        - File size ≤ 5MB
        - Magic bytes indicate JPEG or PNG

    Raises:
        InvalidProductIdError: If product_id is not a valid slug.
        FileTooLargeError: If file exceeds 5MB.
        InvalidImageTypeError: If magic bytes don't match JPEG or PNG.
    """
    # Validate product_id slug format first (before any file path construction)
    if not product_id or not _SLUG_RE.match(product_id):
        raise InvalidProductIdError(
            f"Product ID must match slug format (lowercase alphanumeric + hyphens): {product_id!r}"
        )

    # Check file size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise FileTooLargeError(
            f"File size {len(file_bytes)} bytes exceeds maximum of {MAX_FILE_SIZE} bytes (5MB)"
        )

    # Check magic bytes
    if not (file_bytes[:3] == _JPEG_MAGIC or file_bytes[:4] == _PNG_MAGIC):
        raise InvalidImageTypeError("Unsupported image format. Only JPEG and PNG are accepted.")


def process_image(file_bytes: bytes, product_id: str, static_path: str | None = None) -> dict:
    """Process an image: validate with Pillow, strip EXIF, resize, save as WebP.

    Creates both a main image and a thumbnail.

    Args:
        file_bytes: Raw file bytes (already validated by validate_image_file).
        product_id: Product slug (already validated).
        static_path: Override for static file directory (defaults to settings).

    Returns:
        Dict with image_url and thumbnail_url (relative paths for serving).

    Raises:
        ImageProcessingError: If the image is corrupted or dimensions exceed limits.
    """
    # Defensive validation for direct service callers. The upload route also
    # validates before reading paths, but this function constructs paths too.
    if not product_id or not _SLUG_RE.match(product_id):
        raise InvalidProductIdError(
            f"Product ID must match slug format (lowercase alphanumeric + hyphens): {product_id!r}"
        )

    if static_path is None:
        settings = get_settings()
        static_path = settings.static_file_path

    # Resolve output directory and verify path safety
    base_dir = (Path(static_path).resolve() / "products").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    main_path = (base_dir / f"{product_id}.webp").resolve()
    thumb_path = (base_dir / f"{product_id}_thumb.webp").resolve()

    # Path traversal prevention: ensure resolved paths are under base_dir
    try:
        main_path.relative_to(base_dir)
        thumb_path.relative_to(base_dir)
    except ValueError as e:
        raise ImageProcessingError("Path traversal detected") from e

    # Open and verify with Pillow
    try:
        import io
        import warnings

        img = Image.open(io.BytesIO(file_bytes))
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

    # Convert to RGB if necessary (handles RGBA, P, L modes)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        # Create white background for transparent images
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background

    # Create main image (thumbnail mode preserves aspect ratio, no upscale)
    main_img = img.copy()
    main_img.thumbnail(_MAIN_MAX_SIZE, Image.LANCZOS)
    main_img.save(str(main_path), format="WEBP", quality=_MAIN_QUALITY)

    # Create thumbnail
    thumb_img = img.copy()
    thumb_img.thumbnail(_THUMB_MAX_SIZE, Image.LANCZOS)
    thumb_img.save(str(thumb_path), format="WEBP", quality=_THUMB_QUALITY)

    return {
        "image_url": f"/static/products/{product_id}.webp",
        "thumbnail_url": f"/static/products/{product_id}_thumb.webp",
    }
