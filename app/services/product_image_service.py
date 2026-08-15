"""Product image gallery service.

Owns the product_images aggregate: upload, ordering, primary selection, and
the response fields product readers expose to API clients.
"""

import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import structlog

from app.config import get_settings
from app.database import DbConnection, get_db, require_row
from app.services import object_storage_service
from app.services.image_service import process_image, validate_image_file

logger = structlog.get_logger(__name__)

MAX_IMAGES_PER_PRODUCT = 6


class ProductImageError(Exception):
    """Base class for product image gallery errors."""


class ProductImageLimitError(ProductImageError):
    """Raised when a product already has the maximum number of images."""


class ProductImageNotFoundError(ProductImageError):
    """Raised when an image does not exist for the given product."""


class ProductImageOrderError(ProductImageError):
    """Raised when a reorder request does not match the product image set."""


class ProductNotFoundError(ProductImageError):
    """Raised when a product does not exist."""


def _row_to_image(row: dict) -> dict:
    return {
        "id": row["id"],
        "image_url": row["image_url"],
        "thumbnail_url": row["thumbnail_url"],
        "zoom_url": row["zoom_url"] if "zoom_url" in row.keys() else None,
        "sort_order": row["sort_order"],
        "is_primary": bool(row["is_primary"]),
    }


def _primary_fields(images: list[dict]) -> tuple[str | None, str | None]:
    primary = next((image for image in images if image["is_primary"]), None)
    if primary is None:
        return None, None
    return primary["image_url"], primary["thumbnail_url"]


def with_image_fields(product: dict, images: list[dict]) -> dict:
    """Return a product dict with ordered gallery and computed primary fields."""
    primary_image_url, primary_thumbnail_url = _primary_fields(images)
    result = dict(product)
    result.pop("image_url", None)
    result["images"] = images
    result["primary_image_url"] = primary_image_url
    result["primary_thumbnail_url"] = primary_thumbnail_url
    return result


def images_for_products(conn: DbConnection, product_ids: list[str]) -> dict[str, list[dict]]:
    """Load ordered images for a product id set."""
    if not product_ids:
        return {}
    placeholders = ", ".join("%s" for _ in product_ids)
    rows = conn.execute(
        f"""
        SELECT id, product_id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
        FROM product_images
        WHERE product_id IN ({placeholders})
        ORDER BY product_id, sort_order, created_at, id
        """,  # noqa: S608 - placeholders are generated from product_ids length only.
        product_ids,
    ).fetchall()

    grouped: dict[str, list[dict]] = {product_id: [] for product_id in product_ids}
    for row in rows:
        grouped.setdefault(row["product_id"], []).append(_row_to_image(row))
    return grouped


def attach_image_fields(products: list[dict]) -> list[dict]:
    """Attach images and primary URL fields to product dictionaries."""
    product_ids = [product["id"] for product in products]
    with get_db() as conn:
        grouped = images_for_products(conn, product_ids)
    return [with_image_fields(product, grouped.get(product["id"], [])) for product in products]


def attach_image_fields_one(product: dict) -> dict:
    """Attach images and primary URL fields to one product dictionary."""
    return attach_image_fields([product])[0]


def list_images(product_id: str) -> list[dict]:
    """Return ordered images for a product."""
    with get_db() as conn:
        _ensure_product_exists(conn, product_id)
        return images_for_products(conn, [product_id]).get(product_id, [])


def add_image(product_id: str, file_bytes: bytes) -> dict:
    """Validate, process, and append one image to a product gallery."""
    validate_image_file(file_bytes, product_id)
    image_id = uuid.uuid4().hex

    with get_db() as conn:
        _ensure_product_exists(conn, product_id)
        current = conn.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(MAX(sort_order), -1) AS max_order
            FROM product_images
            WHERE product_id = %s
            """,
            (product_id,),
        ).fetchone()
        current = require_row(current)
        if current["count"] >= MAX_IMAGES_PER_PRODUCT:
            raise ProductImageLimitError(f"Product already has {MAX_IMAGES_PER_PRODUCT} images")

        sort_order = int(current["max_order"]) + 1
        is_primary = 1 if current["count"] == 0 else 0
        processed = process_image(file_bytes, product_id, image_id=image_id)
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, zoom_url,
                sort_order, is_primary, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (
                image_id,
                product_id,
                processed["image_url"],
                processed["thumbnail_url"],
                processed["zoom_url"],
                sort_order,
                is_primary,
            ),
        )
        row = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
            FROM product_images
            WHERE id = %s AND product_id = %s
            """,
            (image_id, product_id),
        ).fetchone()

    return _row_to_image(require_row(row, "product_images row missing after insert"))


def delete_image(product_id: str, image_id: str) -> None:
    """Delete an image row, promote primary when needed, and unlink files."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, zoom_url, is_primary
            FROM product_images
            WHERE product_id = %s AND id = %s
            """,
            (product_id, image_id),
        ).fetchone()
        if row is None:
            raise ProductImageNotFoundError(f"Image not found: {image_id}")

        conn.execute(
            "DELETE FROM product_images WHERE product_id = %s AND id = %s", (product_id, image_id)
        )
        if row["is_primary"]:
            replacement = conn.execute(
                """
                SELECT id
                FROM product_images
                WHERE product_id = %s
                ORDER BY sort_order, created_at, id
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
            if replacement is not None:
                conn.execute(
                    "UPDATE product_images SET is_primary = 1 WHERE product_id = %s AND id = %s",
                    (product_id, replacement["id"]),
                )

    _unlink_image_files(row["image_url"], row["thumbnail_url"], row["zoom_url"])


def delete_images_for_product(product_id: str) -> None:
    """Delete every image row for a product and its backing objects.

    Called from product deactivation (soft-delete). Deleting the objects while
    leaving ``product_images`` rows in place would let a later reactivation
    (``is_active=True``) point at media that no longer exists. So the rows are
    deleted in the same operation, keeping rows and objects consistent — the
    same contract video already uses (``delete_video_if_exists`` removes the
    row). Object removal is best-effort (failures are swallowed/logged inside
    ``_unlink_image_files``); this helper never raises.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT image_url, thumbnail_url, zoom_url
            FROM product_images
            WHERE product_id = %s
            """,
            (product_id,),
        ).fetchall()
        conn.execute("DELETE FROM product_images WHERE product_id = %s", (product_id,))

    for row in rows:
        _unlink_image_files(row["image_url"], row["thumbnail_url"], row["zoom_url"])


def reorder_images(product_id: str, ordered_ids: list[str]) -> list[dict]:
    """Update image sort order without changing the primary image."""
    with get_db() as conn:
        _ensure_product_exists(conn, product_id)
        rows = conn.execute(
            """
            SELECT id
            FROM product_images
            WHERE product_id = %s
            ORDER BY sort_order, created_at, id
            """,
            (product_id,),
        ).fetchall()
        current_ids = [row["id"] for row in rows]
        if set(current_ids) != set(ordered_ids) or len(current_ids) != len(ordered_ids):
            raise ProductImageOrderError("ordered_ids must match all images for the product")
        for sort_order, ordered_id in enumerate(ordered_ids):
            conn.execute(
                "UPDATE product_images SET sort_order = %s WHERE product_id = %s AND id = %s",
                (sort_order, product_id, ordered_id),
            )
        return images_for_products(conn, [product_id]).get(product_id, [])


def set_primary(product_id: str, image_id: str) -> dict:
    """Set exactly one image as primary for a product."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM product_images
            WHERE product_id = %s AND id = %s
            """,
            (product_id, image_id),
        ).fetchone()
        if row is None:
            raise ProductImageNotFoundError(f"Image not found: {image_id}")
        conn.execute(
            "UPDATE product_images SET is_primary = 0 WHERE product_id = %s", (product_id,)
        )
        conn.execute(
            "UPDATE product_images SET is_primary = 1 WHERE product_id = %s AND id = %s",
            (product_id, image_id),
        )
        result = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
            FROM product_images
            WHERE product_id = %s AND id = %s
            """,
            (product_id, image_id),
        ).fetchone()
    return _row_to_image(require_row(result, "product_images row missing after update"))


def add_existing_image_url(product_id: str, image_url: str) -> dict | None:
    """Append an existing URL, used by CSV import compatibility.

    Returns None when the product already has the configured maximum images.
    """
    image_url = _normalize_existing_image_url("image_url", image_url)
    thumbnail_url = _derive_thumbnail_url(image_url)
    return add_existing_image_variants(product_id, image_url, thumbnail_url, None)


def add_existing_image_variants(
    product_id: str,
    image_url: str,
    thumbnail_url: str,
    zoom_url: str | None,
) -> dict | None:
    """Append already-generated image variant URLs to a product gallery.

    Returns None when the product already has the configured maximum images.
    """
    image_url = _normalize_existing_image_url("image_url", image_url)
    thumbnail_url = _normalize_existing_image_url("thumbnail_url", thumbnail_url)
    if zoom_url is not None:
        zoom_url = _normalize_existing_image_url("zoom_url", zoom_url)

    image_id = uuid.uuid4().hex
    with get_db() as conn:
        _ensure_product_exists(conn, product_id)
        current = conn.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(MAX(sort_order), -1) AS max_order
            FROM product_images
            WHERE product_id = %s
            """,
            (product_id,),
        ).fetchone()
        current = require_row(current)
        if current["count"] >= MAX_IMAGES_PER_PRODUCT:
            return None
        is_primary = 1 if current["count"] == 0 else 0
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, zoom_url,
                sort_order, is_primary, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (
                image_id,
                product_id,
                image_url,
                thumbnail_url,
                zoom_url,
                int(current["max_order"]) + 1,
                is_primary,
            ),
        )
        row = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
            FROM product_images
            WHERE id = %s AND product_id = %s
            """,
            (image_id, product_id),
        ).fetchone()
    return _row_to_image(require_row(row, "product_images row missing after URL insert"))


def _ensure_product_exists(conn: DbConnection, product_id: str) -> None:
    row = conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")


def _normalize_existing_image_url(field_name: str, image_url: str) -> str:
    stripped = image_url.strip()
    if not stripped.startswith(("http://", "https://", "/")):
        raise ValueError(f"{field_name} must be http(s) or an absolute relative path")
    return stripped


def _derive_thumbnail_url(image_url: str) -> str:
    split = urlsplit(image_url)
    path = Path(split.path)
    if path.suffix:
        thumb_path = str(path.with_name(f"{path.stem}_thumb{path.suffix}"))
    else:
        thumb_path = f"{split.path.rstrip('/')}_thumb.webp"
    return urlunsplit((split.scheme, split.netloc, thumb_path, split.query, split.fragment))


def _r2_object_key(url: str) -> str | None:
    """Return the R2 object key for a stored URL, or None if it is not ours.

    A URL is considered an R2 object when it starts with the configured public
    base. Legacy ``/static/...`` paths and external absolute URLs (e.g.
    CSV-imported) are not R2 objects and return None.
    """
    base = get_settings().r2_public_base_url
    if not base:
        return None
    prefix = base.rstrip("/") + "/"
    if not url.startswith(prefix):
        return None
    key = url[len(prefix) :]
    return key or None


def _unlink_image_files(*urls: str | None) -> None:
    """Best-effort removal of image variant objects.

    Handles the three URL shapes that can coexist during the migration:
      - R2 public URLs -> delete the object from R2 (best-effort)
      - legacy ``/static/...`` paths -> unlink the file from local disk
      - external absolute URLs -> skip (not owned by us)
    """
    settings = get_settings()
    static_root = Path(settings.static_file_path).resolve()
    for url in urls:
        if not url:
            continue

        key = _r2_object_key(url)
        if key is not None:
            try:
                object_storage_service.delete_object(key)
            except object_storage_service.MediaStorageError as exc:
                logger.warning("product_image_r2_delete_failed", key=key, error=str(exc))
            continue

        if url.startswith("/static/"):
            relative = url.removeprefix("/static/").lstrip("/")
            path = (static_root / relative).resolve()
            try:
                path.relative_to(static_root)
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("product_image_unlink_failed", path=str(path), error=str(exc))
            except ValueError:
                logger.warning("product_image_unlink_rejected", path=str(path))
            continue

        # External absolute URL (e.g. CSV-imported) — not ours to delete.
        logger.debug("product_image_delete_skipped_external", url=url)
