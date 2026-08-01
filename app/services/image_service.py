"""Image service — validation, processing, and storage for product images.

Handles magic-byte validation, Pillow-based resize/conversion, EXIF stripping,
and path-traversal prevention. All images are stored as WebP.
"""

import re
from pathlib import Path

from PIL import Image, ImageOps

from app.config import get_settings

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
    # Validate product_id slug format first (before any file path construction)
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
    """Validate the per-image UUID hex used in file names."""
    if not image_id or not _IMAGE_ID_RE.match(image_id):
        raise InvalidImageIdError(f"Image ID must be a UUID hex string: {image_id!r}")


def process_image(
    file_bytes: bytes,
    product_id: str,
    static_path: str | None = None,
    image_id: str | None = None,
) -> dict:
    """Process an image: validate with Pillow, strip EXIF, resize, save as WebP.

    Creates main, thumbnail, and zoom derivatives.

    Args:
        file_bytes: Raw file bytes (already validated by validate_image_file).
        product_id: Product slug (already validated).
        static_path: Override for static file directory (defaults to settings).
        image_id: Optional UUID hex. When supplied, filenames are unique per image.

    Returns:
        Dict with image_url, thumbnail_url, and zoom_url (relative paths for serving).

    Raises:
        ImageProcessingError: If the image is corrupted or dimensions exceed limits.
    """
    # Defensive validation for direct service callers. The upload route also
    # validates before reading paths, but this function constructs paths too.
    if not product_id or not _SLUG_RE.match(product_id):
        raise InvalidProductIdError(
            f"Product ID must match slug format (lowercase alphanumeric + hyphens): {product_id!r}"
        )
    if image_id is not None:
        validate_image_id(image_id)

    if static_path is None:
        settings = get_settings()
        static_path = settings.static_file_path

    # Resolve output directory and verify path safety
    base_dir = (Path(static_path).resolve() / "products").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    filename_stem = f"{product_id}_{image_id}" if image_id else product_id
    main_path = (base_dir / f"{filename_stem}.webp").resolve()
    thumb_path = (base_dir / f"{filename_stem}_thumb.webp").resolve()
    zoom_path = (base_dir / f"{filename_stem}_zoom.webp").resolve()

    # Path traversal prevention: ensure resolved paths are under base_dir
    try:
        main_path.relative_to(base_dir)
        thumb_path.relative_to(base_dir)
        zoom_path.relative_to(base_dir)
    except ValueError as e:
        raise ImageProcessingError("Path traversal detected") from e

    # Open and verify with Pillow
    try:
        import io
        import warnings

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

    # Create main image (thumbnail mode preserves aspect ratio, no upscale)
    main_img = img.copy()
    main_img.thumbnail(_MAIN_MAX_SIZE, _RESAMPLE_LANCZOS)
    main_img.save(str(main_path), format="WEBP", quality=_MAIN_QUALITY)

    # Create thumbnail
    thumb_img = img.copy()
    thumb_img.thumbnail(_THUMB_MAX_SIZE, _RESAMPLE_LANCZOS)
    thumb_img.save(str(thumb_path), format="WEBP", quality=_THUMB_QUALITY)

    # Create zoom image. It is still a bounded, EXIF-stripped derivative.
    zoom_img = img.copy()
    zoom_img.thumbnail(_ZOOM_MAX_SIZE, _RESAMPLE_LANCZOS)
    zoom_img.save(str(zoom_path), format="WEBP", quality=_ZOOM_QUALITY)

    return {
        "image_url": f"/static/products/{filename_stem}.webp",
        "thumbnail_url": f"/static/products/{filename_stem}_thumb.webp",
        "zoom_url": f"/static/products/{filename_stem}_zoom.webp",
    }
