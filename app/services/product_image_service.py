"""Product image gallery service.

Owns the product_images aggregate: upload, ordering, primary selection, and
the response fields product readers expose to API clients.
"""

import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import structlog

from app.config import get_settings
from app.database import get_db
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


def _row_to_image(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "image_url": row["image_url"],
        "thumbnail_url": row["thumbnail_url"],
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


def images_for_products(conn: sqlite3.Connection, product_ids: list[str]) -> dict[str, list[dict]]:
    """Load ordered images for a product id set."""
    if not product_ids:
        return {}
    placeholders = ", ".join("?" for _ in product_ids)
    rows = conn.execute(
        f"""
        SELECT id, product_id, image_url, thumbnail_url, sort_order, is_primary
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
        conn.execute("BEGIN IMMEDIATE")
        _ensure_product_exists(conn, product_id)
        current = conn.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(MAX(sort_order), -1) AS max_order
            FROM product_images
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()
        if current["count"] >= MAX_IMAGES_PER_PRODUCT:
            raise ProductImageLimitError(f"Product already has {MAX_IMAGES_PER_PRODUCT} images")

        sort_order = int(current["max_order"]) + 1
        is_primary = 1 if current["count"] == 0 else 0
        processed = process_image(file_bytes, product_id, image_id=image_id)
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, sort_order, is_primary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                image_id,
                product_id,
                processed["image_url"],
                processed["thumbnail_url"],
                sort_order,
                is_primary,
            ),
        )
        row = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, sort_order, is_primary
            FROM product_images
            WHERE id = ? AND product_id = ?
            """,
            (image_id, product_id),
        ).fetchone()

    return _row_to_image(row)


def delete_image(product_id: str, image_id: str) -> None:
    """Delete an image row, promote primary when needed, and unlink files."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, is_primary
            FROM product_images
            WHERE product_id = ? AND id = ?
            """,
            (product_id, image_id),
        ).fetchone()
        if row is None:
            raise ProductImageNotFoundError(f"Image not found: {image_id}")

        conn.execute(
            "DELETE FROM product_images WHERE product_id = ? AND id = ?", (product_id, image_id)
        )
        if row["is_primary"]:
            replacement = conn.execute(
                """
                SELECT id
                FROM product_images
                WHERE product_id = ?
                ORDER BY sort_order, created_at, id
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
            if replacement is not None:
                conn.execute(
                    "UPDATE product_images SET is_primary = 1 WHERE product_id = ? AND id = ?",
                    (product_id, replacement["id"]),
                )

    _unlink_image_files(row["image_url"], row["thumbnail_url"])


def reorder_images(product_id: str, ordered_ids: list[str]) -> list[dict]:
    """Update image sort order without changing the primary image."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_product_exists(conn, product_id)
        rows = conn.execute(
            """
            SELECT id
            FROM product_images
            WHERE product_id = ?
            ORDER BY sort_order, created_at, id
            """,
            (product_id,),
        ).fetchall()
        current_ids = [row["id"] for row in rows]
        if set(current_ids) != set(ordered_ids) or len(current_ids) != len(ordered_ids):
            raise ProductImageOrderError("ordered_ids must match all images for the product")
        for sort_order, ordered_id in enumerate(ordered_ids):
            conn.execute(
                "UPDATE product_images SET sort_order = ? WHERE product_id = ? AND id = ?",
                (sort_order, product_id, ordered_id),
            )
        return images_for_products(conn, [product_id]).get(product_id, [])


def set_primary(product_id: str, image_id: str) -> dict:
    """Set exactly one image as primary for a product."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT id
            FROM product_images
            WHERE product_id = ? AND id = ?
            """,
            (product_id, image_id),
        ).fetchone()
        if row is None:
            raise ProductImageNotFoundError(f"Image not found: {image_id}")
        conn.execute("UPDATE product_images SET is_primary = 0 WHERE product_id = ?", (product_id,))
        conn.execute(
            "UPDATE product_images SET is_primary = 1 WHERE product_id = ? AND id = ?",
            (product_id, image_id),
        )
        result = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, sort_order, is_primary
            FROM product_images
            WHERE product_id = ? AND id = ?
            """,
            (product_id, image_id),
        ).fetchone()
    return _row_to_image(result)


def add_existing_image_url(product_id: str, image_url: str) -> dict | None:
    """Append an existing URL, used by CSV import compatibility.

    Returns None when the product already has the configured maximum images.
    """
    if not image_url.startswith(("http://", "https://", "/")):
        raise ValueError("image_url must be http(s) or an absolute relative path")
    image_id = uuid.uuid4().hex
    thumbnail_url = _derive_thumbnail_url(image_url)
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_product_exists(conn, product_id)
        current = conn.execute(
            """
            SELECT COUNT(*) AS count, COALESCE(MAX(sort_order), -1) AS max_order
            FROM product_images
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()
        if current["count"] >= MAX_IMAGES_PER_PRODUCT:
            return None
        is_primary = 1 if current["count"] == 0 else 0
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, sort_order, is_primary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                image_id,
                product_id,
                image_url,
                thumbnail_url,
                int(current["max_order"]) + 1,
                is_primary,
            ),
        )
        row = conn.execute(
            """
            SELECT id, image_url, thumbnail_url, sort_order, is_primary
            FROM product_images
            WHERE id = ? AND product_id = ?
            """,
            (image_id, product_id),
        ).fetchone()
    return _row_to_image(row)


def _ensure_product_exists(conn: sqlite3.Connection, product_id: str) -> None:
    row = conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")


def _derive_thumbnail_url(image_url: str) -> str:
    split = urlsplit(image_url)
    path = Path(split.path)
    if path.suffix:
        thumb_path = str(path.with_name(f"{path.stem}_thumb{path.suffix}"))
    else:
        thumb_path = f"{split.path.rstrip('/')}_thumb.webp"
    return urlunsplit((split.scheme, split.netloc, thumb_path, split.query, split.fragment))


def _unlink_image_files(*urls: str) -> None:
    settings = get_settings()
    static_root = Path(settings.static_file_path).resolve()
    for url in urls:
        if not url.startswith("/static/"):
            continue
        relative = url.removeprefix("/static/").lstrip("/")
        path = (static_root / relative).resolve()
        try:
            path.relative_to(static_root)
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("product_image_unlink_failed", path=str(path), error=str(exc))
        except ValueError:
            logger.warning("product_image_unlink_rejected", path=str(path))
