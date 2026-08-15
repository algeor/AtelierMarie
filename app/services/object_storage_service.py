"""S3-compatible object storage service for product media (Cloudflare R2).

This is the ONLY module allowed to import ``boto3`` / touch the S3 API. It owns
uploads, deletes, and public-URL generation for product image and video objects.
The R2 client is constructed lazily and module-cached so importing this module
has no side effects (safe at test collection) and the app boots without R2
configured — only the write/delete paths fail (with a clear error) when unset.

Object keys reuse the existing on-disk filename stems under a ``products/``
prefix so keys stay predictable and the disk->R2 backfill is a mechanical
``/static/products/X`` -> ``products/X`` mapping.

Test seam: :func:`set_backend` injects a fake in-memory backend (key->bytes) so
tests never hit a live bucket or require credentials.
"""

import re
import threading
from typing import Protocol

import structlog

from app.config import get_settings

_logger = structlog.get_logger(__name__)

# Product IDs are slugs (e.g. ``lavender-dream-300ml``). Validating against this
# allowlist BEFORE constructing any object key is more robust than blocklisting
# traversal characters and guarantees the derived key stays under ``products/``.
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

_KEY_PREFIX = "products/"


class MediaStorageError(Exception):
    """Raised when an object storage operation fails.

    Wraps botocore/boto3 internals so callers (routes/services) never see raw
    S3 client exceptions and can translate to a clean 5xx/502 envelope.
    """


class StorageConfigError(MediaStorageError):
    """Raised from a write/delete path when required R2_* settings are unset."""


class StorageBackend(Protocol):
    """Minimal storage backend contract, satisfied by the R2 client wrapper and
    the in-memory test fake."""

    def put_object(self, key: str, data: bytes, content_type: str) -> None: ...

    def delete_object(self, key: str) -> None: ...


# --- Backend construction (lazy, module-cached) ---------------------------------

_backend: StorageBackend | None = None
_backend_lock = threading.Lock()


class _R2Backend:
    """boto3 S3 client wrapper targeting Cloudflare R2. Constructed only when a
    write/delete is actually invoked with R2 configured."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> None:
        # boto3 is imported here (not at module top) so this dependency and the
        # S3 API surface stay confined to the write path of this one module.
        import boto3
        from botocore.config import Config

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
        except (BotoCoreError, ClientError) as exc:
            msg = f"Failed to upload object {key!r} to R2"
            raise MediaStorageError(msg) from exc

    def delete_object(self, key: str) -> None:
        from botocore.exceptions import BotoCoreError, ClientError

        # S3 DeleteObject is already idempotent (deleting a missing key succeeds).
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            msg = f"Failed to delete object {key!r} from R2"
            raise MediaStorageError(msg) from exc


def set_backend(backend: StorageBackend | None) -> None:
    """Inject a storage backend (test seam). Pass ``None`` to reset to the
    lazily-constructed R2 backend."""
    global _backend
    with _backend_lock:
        _backend = backend


def _get_backend() -> StorageBackend:
    global _backend
    if _backend is not None:
        return _backend
    with _backend_lock:
        if _backend is not None:
            return _backend
        settings = get_settings()
        missing = [
            name
            for name, value in (
                ("R2_BUCKET", settings.r2_bucket),
                ("R2_ENDPOINT_URL", settings.r2_endpoint_url),
                ("R2_ACCESS_KEY_ID", settings.r2_access_key_id),
                ("R2_SECRET_ACCESS_KEY", settings.r2_secret_access_key),
                ("R2_PUBLIC_BASE_URL", settings.r2_public_base_url),
            )
            if not value
        ]
        if missing:
            msg = f"Object storage is not configured; set: {', '.join(missing)}"
            raise StorageConfigError(msg)
        _backend = _R2Backend(
            bucket=settings.r2_bucket,
            endpoint_url=settings.r2_endpoint_url,
            access_key_id=settings.r2_access_key_id,
            secret_access_key=settings.r2_secret_access_key,
        )
        return _backend


# --- Public URL generation ------------------------------------------------------


def public_url(key: str) -> str:
    """Join the configured public base URL with ``key`` (exactly one slash)."""
    base = get_settings().r2_public_base_url
    if not base:
        msg = "Object storage is not configured; set: R2_PUBLIC_BASE_URL"
        raise StorageConfigError(msg)
    return f"{base.rstrip('/')}/{key.lstrip('/')}"


# --- Object-key derivation ------------------------------------------------------


def _validate_product_id(product_id: str) -> None:
    if not _SLUG_PATTERN.match(product_id):
        msg = f"Invalid product_id for object key: {product_id!r}"
        raise MediaStorageError(msg)


def _key(stem: str, suffix: str) -> str:
    key = f"{_KEY_PREFIX}{stem}{suffix}"
    # Defensive: the derived key must stay under the products/ prefix and never
    # escape via traversal. The slug allowlist already guarantees this; this is
    # a belt-and-suspenders check.
    if ".." in key or not key.startswith(_KEY_PREFIX):
        msg = f"Derived object key escapes the products/ prefix: {key!r}"
        raise MediaStorageError(msg)
    return key


def image_stem(product_id: str, image_id: str) -> str:
    """Return the shared filename stem for an image's variants."""
    _validate_product_id(product_id)
    return f"{product_id}_{image_id}"


def object_key_for_image(product_id: str, image_id: str) -> str:
    """Key for the main image variant: ``products/{product_id}_{image_id}.webp``."""
    return _key(image_stem(product_id, image_id), ".webp")


def object_key_for_image_thumb(product_id: str, image_id: str) -> str:
    """Key for the thumbnail variant: ``..._thumb.webp``."""
    return _key(image_stem(product_id, image_id), "_thumb.webp")


def object_key_for_image_zoom(product_id: str, image_id: str) -> str:
    """Key for the zoom variant: ``..._zoom.webp``."""
    return _key(image_stem(product_id, image_id), "_zoom.webp")


def object_key_for_stem(stem: str, suffix: str) -> str:
    """Key for an arbitrary reused filename stem under ``products/``.

    ``stem`` is a filename stem already derived elsewhere (e.g. the image
    service's ``{product_id}_{image_id}``); it must not contain path separators
    or traversal. ``suffix`` is the variant suffix + extension, e.g. ``.webp``,
    ``_thumb.webp``, ``_video.mp4``.
    """
    if "/" in stem or "\\" in stem or ".." in stem:
        msg = f"Invalid object-key stem: {stem!r}"
        raise MediaStorageError(msg)
    return _key(stem, suffix)


def object_key_for_video(product_id: str, video_id: str) -> str:
    """Key for the transcoded MP4: ``products/{product_id}_{video_id}_video.mp4``."""
    _validate_product_id(product_id)
    return _key(f"{product_id}_{video_id}", "_video.mp4")


def object_key_for_video_poster(product_id: str, video_id: str) -> str:
    """Key for the video poster: ``products/{product_id}_{video_id}_poster.webp``."""
    _validate_product_id(product_id)
    return _key(f"{product_id}_{video_id}", "_poster.webp")


# --- Write / delete -------------------------------------------------------------


def upload_bytes(key: str, data: bytes, content_type: str) -> str:
    """Upload ``data`` to ``key`` with ``content_type``; return the public URL.

    Raises :class:`StorageConfigError` if R2 is unconfigured and
    :class:`MediaStorageError` (wrapping botocore) on S3 failures.
    """
    _get_backend().put_object(key, data, content_type)
    return public_url(key)


def delete_object(key: str) -> None:
    """Delete ``key`` (idempotent — a missing object is success).

    Raises :class:`StorageConfigError` if R2 is unconfigured and
    :class:`MediaStorageError` (wrapping botocore) on S3 failures. Callers on
    the cleanup path treat failures as best-effort (log, do not abort).
    """
    _get_backend().delete_object(key)
