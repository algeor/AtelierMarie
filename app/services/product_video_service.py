"""Product video orchestration and async transcode pipeline."""

import concurrent.futures
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

from app.config import get_settings
from app.constants import SQLITE_DATETIME_FORMAT, VIDEO_TRANSCODE_LEASE_SECONDS
from app.database import get_db
from app.services import object_storage_service, video_service

logger = structlog.get_logger(__name__)


class ProductVideoError(Exception):
    """Base class for product video errors."""


class ProductNotFoundError(ProductVideoError):
    """Raised when a product does not exist."""


class ProductVideoNotFoundError(ProductVideoError):
    """Raised when a product has no video row."""


class ProductVideoProcessingConflictError(ProductVideoError):
    """Raised when upload replacement races with an in-flight transcode."""


LEASE_REFRESH_INTERVAL_SECONDS = min(60, max(1, VIDEO_TRANSCODE_LEASE_SECONDS // 3))


def _now() -> str:
    return datetime.now(UTC).strftime(SQLITE_DATETIME_FORMAT)


def _lease_deadline() -> str:
    return (datetime.now(UTC) + timedelta(seconds=VIDEO_TRANSCODE_LEASE_SECONDS)).strftime(
        SQLITE_DATETIME_FORMAT
    )


def _fmt_ts(value: object) -> str | None:
    """Normalize a TIMESTAMPTZ value (psycopg returns ``datetime``) to the
    canonical ``%Y-%m-%d %H:%M:%S`` string the ``ProductVideo`` model expects.

    Postgres columns come back as ``datetime`` objects; Pydantic's ``str`` field
    rejects them, so downstream reads 500 unless we render them here (mirrors the
    ``_fmt_ts`` helpers in the other services touched by the Postgres port).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(SQLITE_DATETIME_FORMAT)
    return str(value)


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
        "created_at": _fmt_ts(row["created_at"]),
        "updated_at": _fmt_ts(row["updated_at"]),
    }


def _public_video(row: sqlite3.Row | None) -> dict | None:
    if row is None or row["status"] != "ready":
        return None
    return _row_to_video(row)


def _ensure_product_exists(conn: sqlite3.Connection, product_id: str) -> None:
    row = conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")


def _ensure_no_processing_video(conn: sqlite3.Connection, product_id: str) -> None:
    existing = conn.execute(
        "SELECT status FROM product_videos WHERE product_id = %s",
        (product_id,),
    ).fetchone()
    if existing is not None and existing["status"] in ("queued", "transcoding"):
        raise ProductVideoProcessingConflictError("video is still processing")


def validate_upload_target(product_id: str) -> None:
    """Validate product existence and reject uploads that cannot be accepted."""
    video_service.validate_product_id(product_id)
    with get_db() as conn:
        _ensure_product_exists(conn, product_id)
        _ensure_no_processing_video(conn, product_id)


def _video_rows_for_products(
    conn: sqlite3.Connection, product_ids: list[str]
) -> dict[str, sqlite3.Row]:
    if not product_ids:
        return {}
    placeholders = ", ".join("%s" for _ in product_ids)
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
        WHERE product_id = %s
        ORDER BY is_primary DESC, sort_order, created_at, id
        LIMIT 1
        """,
        (product_id,),
    ).fetchone()
    if row is None:
        return None
    return row["thumbnail_url"] or row["image_url"]


def _save_temp_upload(file_bytes: bytes, product_id: str, video_id: str) -> Path:
    temp_path = reserve_temp_upload(product_id, video_id=video_id)
    temp_path.write_bytes(file_bytes)
    return temp_path


def reserve_temp_upload(product_id: str, *, video_id: str | None = None) -> Path:
    """Reserve a private temp path for streaming an upload directly to disk."""
    video_service.validate_product_id(product_id)
    video_id = video_id or uuid.uuid4().hex
    video_service.validate_video_id(video_id)
    settings = get_settings()
    temp_root = Path(settings.video_upload_temp_path).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_path = (temp_root / f"{product_id}_{video_id}.upload").resolve()
    try:
        temp_path.relative_to(temp_root)
    except ValueError as exc:
        raise video_service.VideoProcessingError("Path traversal detected") from exc
    return temp_path


def _video_id_from_temp_path(temp_path: Path, product_id: str) -> str:
    prefix = f"{product_id}_"
    suffix = ".upload"
    name = temp_path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        raise video_service.VideoProcessingError("Invalid upload temp path")
    video_id = name[len(prefix) : -len(suffix)]
    video_service.validate_video_id(video_id)
    return video_id


def _validate_temp_path(temp_path: str | Path) -> Path:
    settings = get_settings()
    temp_root = Path(settings.video_upload_temp_path).resolve()
    resolved = Path(temp_path).resolve()
    try:
        resolved.relative_to(temp_root)
    except ValueError as exc:
        raise video_service.VideoProcessingError("Path traversal detected") from exc
    return resolved


def queue_video_upload(product_id: str, file_bytes: bytes) -> dict:
    """Validate a video upload, store the original, and queue async transcode."""
    validate_upload_target(product_id)

    video_id = uuid.uuid4().hex
    temp_path = _save_temp_upload(file_bytes, product_id, video_id)
    return queue_video_upload_path(product_id, temp_path, video_id=video_id)


def queue_video_upload_path(
    product_id: str, temp_path: str | Path, *, video_id: str | None = None
) -> dict:
    """Validate a staged upload path and queue async transcode."""
    video_service.validate_product_id(product_id)
    temp_path = _validate_temp_path(temp_path)
    video_id = video_id or _video_id_from_temp_path(temp_path, product_id)
    video_service.validate_video_id(video_id)
    try:
        validate_upload_target(product_id)
        probe = video_service.validate_video_upload(temp_path, product_id)
        old_files: tuple[str | None, str | None, str | None] = (None, None, None)
        with get_db() as conn:
            _ensure_product_exists(conn, product_id)
            existing = conn.execute(
                "SELECT * FROM product_videos WHERE product_id = %s",
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
                conn.execute("DELETE FROM product_videos WHERE product_id = %s", (product_id,))
            conn.execute(
                """
                INSERT INTO product_videos (
                    id, product_id, status, source_path, duration_secs, sort_order,
                    failure_reason, created_at, updated_at
                ) VALUES (%s, %s, 'queued', %s, %s, 0, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (video_id, product_id, str(temp_path), probe["duration_secs"]),
            )
            row = conn.execute("SELECT * FROM product_videos WHERE id = %s", (video_id,)).fetchone()
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
            "SELECT * FROM product_videos WHERE product_id = %s", (product_id,)
        ).fetchone()
    if row is None:
        raise ProductVideoNotFoundError(f"Product video not found: {product_id}")
    return _row_to_video(row)


def delete_video(product_id: str) -> None:
    """Delete a product video row and unlink all associated files."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM product_videos WHERE product_id = %s", (product_id,)
        ).fetchone()
        if row is None:
            raise ProductVideoNotFoundError(f"Product video not found: {product_id}")
        if row["status"] == "transcoding":
            raise ProductVideoProcessingConflictError("video is still processing")
        conn.execute("DELETE FROM product_videos WHERE product_id = %s", (product_id,))
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
        _ensure_product_exists(conn, product_id)
        cursor = conn.execute(
            """
            UPDATE product_videos
            SET sort_order = %s, updated_at = CURRENT_TIMESTAMP
            WHERE product_id = %s
            """,
            (sort_order, product_id),
        )
        if cursor.rowcount == 0:
            raise ProductVideoNotFoundError(f"Product video not found: {product_id}")
        row = conn.execute(
            "SELECT * FROM product_videos WHERE product_id = %s", (product_id,)
        ).fetchone()
    return _row_to_video(row)


def _staged_output_paths_for_row(row: sqlite3.Row) -> tuple[str, str]:
    """Local temp paths where transcode outputs for ``row`` would be staged.

    Used to clean up partial ffmpeg outputs of an interrupted/expired transcode.
    Only fully-successful transcodes reach R2, so a not-yet-ready row can only
    have leftovers on local disk, never in the object store.
    """
    video_path, poster_path = video_service.output_paths(row["product_id"], row["id"])
    return (str(video_path), str(poster_path))


def _mark_expired_transcodes_failed(conn: sqlite3.Connection) -> tuple[int, list[str | None]]:
    now = _now()
    expired = conn.execute(
        """
        SELECT *
        FROM product_videos
        WHERE status = 'transcoding'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at < %s
        """,
        (now,),
    ).fetchall()
    cursor = conn.execute(
        """
        UPDATE product_videos
        SET status = 'failed', failure_reason = 'processing interrupted',
            source_path = NULL, lease_expires_at = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE status = 'transcoding'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at < %s
        """,
        (now,),
    )
    cleanup: list[str | None] = []
    for row in expired:
        video_path, poster_path = _staged_output_paths_for_row(row)
        cleanup.extend([row["source_path"], video_path, poster_path])
    return cursor.rowcount, cleanup


def _refresh_lease(video_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE product_videos
            SET lease_expires_at = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status = 'transcoding'
            """,
            (_lease_deadline(), video_id),
        )


def _run_with_lease_refresh(video_id: str, fn, *args):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args)
        while True:
            try:
                return future.result(timeout=LEASE_REFRESH_INTERVAL_SECONDS)
            except concurrent.futures.TimeoutError:
                _refresh_lease(video_id)


def _update_ready_if_owned(video_id: str, video_url: str, poster_url: str | None) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE product_videos
            SET status = 'ready', video_url = %s, poster_url = %s, source_path = NULL,
                failure_reason = NULL, lease_expires_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status = 'transcoding'
            """,
            (video_url, poster_url, video_id),
        )
    return cursor.rowcount == 1


def _update_failed_if_owned(video_id: str, failure_reason: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE product_videos
            SET status = 'failed', failure_reason = %s, source_path = NULL,
                lease_expires_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status = 'transcoding'
            """,
            (failure_reason, video_id),
        )
    return cursor.rowcount == 1


def _claim_one_queued(conn: sqlite3.Connection) -> sqlite3.Row | None:
    now = _now()
    live = conn.execute(
        """
        SELECT 1
        FROM product_videos
        WHERE status = 'transcoding'
          AND lease_expires_at IS NOT NULL
          AND lease_expires_at > %s
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
        SET status = 'transcoding', lease_expires_at = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND status = 'queued'
        """,
        (_lease_deadline(), row["id"]),
    )
    if cursor.rowcount != 1:
        return None
    return conn.execute("SELECT * FROM product_videos WHERE id = %s", (row["id"],)).fetchone()


def _upload_transcode_outputs(
    product_id: str, video_id: str, video_path: str, poster_path: str | None
) -> tuple[str, str | None]:
    """Upload staged MP4 (and poster, if any) to R2; return their public URLs.

    Reads the local ffmpeg outputs and uploads them under their derived object
    keys. Raises :class:`object_storage_service.MediaStorageError` on failure so
    the caller can route the row through the fail/cleanup path (no ``ready``
    transition on an upload error). ``poster_path`` is ``None`` when poster
    extraction fell back to a primary thumbnail URL (already stored, nothing to
    upload here).
    """
    video_key = object_storage_service.object_key_for_video(product_id, video_id)
    video_url = object_storage_service.upload_bytes(
        video_key, Path(video_path).read_bytes(), "video/mp4"
    )
    poster_url: str | None = None
    if poster_path is not None:
        poster_key = object_storage_service.object_key_for_video_poster(product_id, video_id)
        try:
            poster_url = object_storage_service.upload_bytes(
                poster_key, Path(poster_path).read_bytes(), "image/webp"
            )
        except object_storage_service.MediaStorageError:
            # The MP4 already landed in R2; a failed poster upload would leave it
            # orphaned (the row never goes ``ready``). Best-effort delete it
            # before re-raising so a partial upload leaves nothing behind.
            try:
                object_storage_service.delete_object(video_key)
            except object_storage_service.MediaStorageError as cleanup_exc:
                logger.warning(
                    "product_video_orphan_cleanup_failed",
                    key=video_key,
                    error=str(cleanup_exc),
                )
            raise
    return video_url, poster_url


def drain_video_transcodes() -> int:
    """Run one video transcode job if available; return changed row count."""
    with get_db() as conn:
        changed, cleanup_files = _mark_expired_transcodes_failed(conn)
        claimed = _claim_one_queued(conn)

    if cleanup_files:
        video_service.unlink_video_files(*cleanup_files)

    if claimed is None:
        return changed

    processed = 1
    staged_video_path, staged_poster_path = _staged_output_paths_for_row(claimed)
    # Local ffmpeg outputs + the raw source are the only artifacts to clean on
    # failure: R2 objects are written only after a fully successful transcode,
    # so a failed job never leaves a durable object to delete.
    cleanup_on_failure: list[str | None] = [
        claimed["source_path"],
        staged_video_path,
        staged_poster_path,
    ]
    try:
        _run_with_lease_refresh(
            claimed["id"],
            video_service.transcode,
            claimed["source_path"],
            claimed["product_id"],
            claimed["id"],
        )
        poster_source_path: str | None = None
        fallback_poster_url: str | None = None
        try:
            poster = _run_with_lease_refresh(
                claimed["id"],
                video_service.extract_poster,
                staged_video_path,
                claimed["product_id"],
                claimed["id"],
            )
            poster_source_path = poster["poster_path"]
        except video_service.VideoServiceError as exc:
            logger.warning("product_video_poster_fallback", video_id=claimed["id"], error=str(exc))
            with get_db() as conn:
                fallback_poster_url = _primary_thumbnail(conn, claimed["product_id"])
            if fallback_poster_url is None:
                logger.warning(
                    "product_video_poster_unavailable",
                    video_id=claimed["id"],
                    error=str(exc),
                )

        video_url, uploaded_poster_url = _run_with_lease_refresh(
            claimed["id"],
            _upload_transcode_outputs,
            claimed["product_id"],
            claimed["id"],
            staged_video_path,
            poster_source_path,
        )
        poster_url = uploaded_poster_url if poster_source_path is not None else fallback_poster_url

        if not _update_ready_if_owned(claimed["id"], video_url, poster_url):
            logger.warning(
                "product_video_ready_update_skipped",
                video_id=claimed["id"],
                reason="row no longer transcoding",
            )
        # Durable copies now live in R2; drop the raw source and staged outputs.
        video_service.unlink_video_files(
            claimed["source_path"], staged_video_path, staged_poster_path
        )
    except Exception as exc:
        logger.warning("product_video_transcode_failed", video_id=claimed["id"], error=str(exc))
        video_service.unlink_video_files(*cleanup_on_failure)
        if not _update_failed_if_owned(claimed["id"], str(exc)):
            logger.warning(
                "product_video_failed_update_skipped",
                video_id=claimed["id"],
                reason="row no longer transcoding",
            )
    return changed + processed
