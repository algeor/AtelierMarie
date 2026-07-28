"""Product video orchestration and async transcode pipeline."""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

from app.config import get_settings
from app.constants import SQLITE_DATETIME_FORMAT, VIDEO_TRANSCODE_LEASE_SECONDS
from app.database import get_db
from app.services import video_service

logger = structlog.get_logger(__name__)


class ProductVideoError(Exception):
    """Base class for product video errors."""


class ProductNotFoundError(ProductVideoError):
    """Raised when a product does not exist."""


class ProductVideoNotFoundError(ProductVideoError):
    """Raised when a product has no video row."""


class ProductVideoProcessingConflictError(ProductVideoError):
    """Raised when upload replacement races with an in-flight transcode."""


def _now() -> str:
    return datetime.now(UTC).strftime(SQLITE_DATETIME_FORMAT)


def _lease_deadline() -> str:
    return (datetime.now(UTC) + timedelta(seconds=VIDEO_TRANSCODE_LEASE_SECONDS)).strftime(
        SQLITE_DATETIME_FORMAT
    )


def _row_to_video(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "status": row["status"],
        "video_url": row["video_url"],
        "poster_url": row["poster_url"],
        "duration_secs": row["duration_secs"],
        "sort_order": row["sort_order"],
        "failure_reason": row["failure_reason"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _public_video(row: sqlite3.Row | None) -> dict | None:
    if row is None or row["status"] != "ready":
        return None
    return _row_to_video(row)


def _ensure_product_exists(conn: sqlite3.Connection, product_id: str) -> None:
    row = conn.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")


def _video_rows_for_products(
    conn: sqlite3.Connection, product_ids: list[str]
) -> dict[str, sqlite3.Row]:
    if not product_ids:
        return {}
    placeholders = ", ".join("?" for _ in product_ids)
    rows = conn.execute(
        f"""
        SELECT *
        FROM product_videos
        WHERE product_id IN ({placeholders})
        """,  # noqa: S608 - placeholders are generated from product_ids length only.
        product_ids,
    ).fetchall()
    return {row["product_id"]: row for row in rows}


def attach_video_fields(products: list[dict], *, public_only: bool = True) -> list[dict]:
    """Attach a `video` field to products; public responses expose ready videos only."""
    product_ids = [product["id"] for product in products]
    with get_db() as conn:
        grouped = _video_rows_for_products(conn, product_ids)

    result: list[dict] = []
    for product in products:
        row = grouped.get(product["id"])
        item = dict(product)
        item["video"] = _public_video(row) if public_only else (_row_to_video(row) if row else None)
        result.append(item)
    return result


def attach_video_fields_one(product: dict, *, public_only: bool = True) -> dict:
    return attach_video_fields([product], public_only=public_only)[0]


def _primary_thumbnail(conn: sqlite3.Connection, product_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT thumbnail_url, image_url
        FROM product_images
        WHERE product_id = ?
        ORDER BY is_primary DESC, sort_order, created_at, id
        LIMIT 1
        """,
        (product_id,),
    ).fetchone()
    if row is None:
        return None
    return row["thumbnail_url"] or row["image_url"]


def _save_temp_upload(file_bytes: bytes, product_id: str, video_id: str) -> Path:
    settings = get_settings()
    temp_root = Path(settings.video_upload_temp_path).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_path = (temp_root / f"{product_id}_{video_id}.upload").resolve()
    try:
        temp_path.relative_to(temp_root)
    except ValueError as exc:
        raise video_service.VideoProcessingError("Path traversal detected") from exc
    temp_path.write_bytes(file_bytes)
    return temp_path


def queue_video_upload(product_id: str, file_bytes: bytes) -> dict:
    """Validate a video upload, store the original, and queue async transcode."""
    video_service.validate_product_id(product_id)
    with get_db() as conn:
        _ensure_product_exists(conn, product_id)

    video_id = uuid.uuid4().hex
    temp_path = _save_temp_upload(file_bytes, product_id, video_id)
    try:
        probe = video_service.validate_video_upload(temp_path, product_id)
        old_files: tuple[str | None, str | None, str | None] = (None, None, None)
        with get_db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            _ensure_product_exists(conn, product_id)
            existing = conn.execute(
                "SELECT * FROM product_videos WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            if existing is not None and existing["status"] in ("queued", "transcoding"):
                raise ProductVideoProcessingConflictError("video is still processing")
            if existing is not None:
                old_files = (
                    existing["video_url"],
                    existing["poster_url"],
                    existing["source_path"],
                )
                conn.execute("DELETE FROM product_videos WHERE product_id = ?", (product_id,))
            conn.execute(
                """
                INSERT INTO product_videos (
                    id, product_id, status, source_path, duration_secs, sort_order,
                    failure_reason, created_at, updated_at
                ) VALUES (?, ?, 'queued', ?, ?, 0, NULL, datetime('now'), datetime('now'))
                """,
                (video_id, product_id, str(temp_path), probe["duration_secs"]),
            )
            row = conn.execute("SELECT * FROM product_videos WHERE id = ?", (video_id,)).fetchone()
        video_service.unlink_video_files(*old_files)
        return _row_to_video(row)
    except Exception:
        video_service.unlink_video_files(str(temp_path))
        raise


def get_video(product_id: str) -> dict:
    """Return the current product video row for admin status views."""
    with get_db() as conn:
        _ensure_product_exists(conn, product_id)
        row = conn.execute(
            "SELECT * FROM product_videos WHERE product_id = ?", (product_id,)
        ).fetchone()
    if row is None:
        raise ProductVideoNotFoundError(f"Product video not found: {product_id}")
    return _row_to_video(row)


def delete_video(product_id: str) -> None:
    """Delete a product video row and unlink all associated files."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM product_videos WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise ProductVideoNotFoundError(f"Product video not found: {product_id}")
        conn.execute("DELETE FROM product_videos WHERE product_id = ?", (product_id,))
    video_service.unlink_video_files(row["video_url"], row["poster_url"], row["source_path"])


def delete_video_if_exists(product_id: str) -> None:
    """Best-effort product-delete hook; no-op when the product has no video."""
    try:
        delete_video(product_id)
    except ProductVideoNotFoundError:
        return


def update_sort_order(product_id: str, sort_order: int) -> dict:
    """Set the insertion index used by the frontend gallery merge."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_product_exists(conn, product_id)
        cursor = conn.execute(
            """
            UPDATE product_videos
            SET sort_order = ?, updated_at = datetime('now')
            WHERE product_id = ?
            """,
            (sort_order, product_id),
        )
        if cursor.rowcount == 0:
            raise ProductVideoNotFoundError(f"Product video not found: {product_id}")
        row = conn.execute(
            "SELECT * FROM product_videos WHERE product_id = ?", (product_id,)
        ).fetchone()
    return _row_to_video(row)


def _mark_expired_transcodes_failed(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        """
        UPDATE product_videos
        SET status = 'failed', failure_reason = 'processing interrupted',
            lease_expires_at = NULL, updated_at = datetime('now')
        WHERE status = 'transcoding'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at < ?
        """,
        (_now(),),
    )
    return cursor.rowcount


def _claim_one_queued(conn: sqlite3.Connection) -> sqlite3.Row | None:
    now = _now()
    live = conn.execute(
        """
        SELECT 1
        FROM product_videos
        WHERE status = 'transcoding'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at > ?
        LIMIT 1
        """,
        (now,),
    ).fetchone()
    if live is not None:
        return None
    row = conn.execute(
        """
        SELECT *
        FROM product_videos
        WHERE status = 'queued'
        ORDER BY created_at, id
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    cursor = conn.execute(
        """
        UPDATE product_videos
        SET status = 'transcoding', lease_expires_at = ?, updated_at = datetime('now')
        WHERE id = ? AND status = 'queued'
        """,
        (_lease_deadline(), row["id"]),
    )
    if cursor.rowcount != 1:
        return None
    return conn.execute("SELECT * FROM product_videos WHERE id = ?", (row["id"],)).fetchone()


def drain_video_transcodes() -> int:
    """Run one video transcode job if available; return changed row count."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        changed = _mark_expired_transcodes_failed(conn)
        claimed = _claim_one_queued(conn)

    if claimed is None:
        return changed

    processed = 1
    try:
        transcoded = video_service.transcode(
            claimed["source_path"], claimed["product_id"], claimed["id"]
        )
        try:
            static_root = Path(get_settings().static_file_path).resolve()
            video_path = (
                static_root / transcoded["video_url"].removeprefix("/static/").lstrip("/")
            ).resolve()
            poster = video_service.extract_poster(video_path, claimed["product_id"], claimed["id"])
            poster_url = poster["poster_url"]
        except video_service.VideoServiceError as exc:
            logger.warning("product_video_poster_fallback", video_id=claimed["id"], error=str(exc))
            with get_db() as conn:
                poster_url = _primary_thumbnail(conn, claimed["product_id"])

        with get_db() as conn:
            conn.execute(
                """
                UPDATE product_videos
                SET status = 'ready', video_url = ?, poster_url = ?, source_path = NULL,
                    failure_reason = NULL, lease_expires_at = NULL, updated_at = datetime('now')
                WHERE id = ?
                """,
                (transcoded["video_url"], poster_url, claimed["id"]),
            )
        video_service.unlink_video_files(claimed["source_path"])
    except Exception as exc:
        logger.warning("product_video_transcode_failed", video_id=claimed["id"], error=str(exc))
        with get_db() as conn:
            conn.execute(
                """
                UPDATE product_videos
                SET status = 'failed', failure_reason = ?, lease_expires_at = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (str(exc), claimed["id"]),
            )
    return changed + processed
