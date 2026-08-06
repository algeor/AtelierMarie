"""One-time backfill of on-disk product media to Cloudflare R2.

Iterates every ``product_images`` and ``product_videos`` row, and for each URL
column still pointing at the legacy ``/static/products/...`` scheme:

  1. Resolves the backing file on local disk (``{static_file_path}/products/X``).
  2. Uploads it to R2 under the derived key (``products/X`` — the same filename
     stem, mechanical mapping — see design.md Decision 6).
  3. Rewrites the DB column to the R2 public URL.

Properties:
  - **Idempotent:** rows whose URLs already point at the R2 public base are
    skipped, so re-running after a partial run only processes what remains.
  - **Resumable:** each row is committed on its own (per-row commit), so an
    interruption never loses completed work and a re-run picks up cleanly.
  - **``--dry-run``:** reports exactly what *would* happen (upload/skip/missing
    counts) without uploading anything or writing the DB.
  - **External URLs untouched:** absolute ``http(s)`` URLs that are not under the
    R2 public base (e.g. CSV-imported product images) are left exactly as-is.
  - **Missing files are non-fatal:** a ``/static/...`` URL with no file on disk
    is logged and counted, and the run continues.
  - **Rewrite log:** every DB rewrite (old URL -> new URL, keyed by table + row
    id + column) is appended to a JSONL log so a rollback can reverse-map R2
    URLs back to their original ``/static/...`` values.

Usage::

    .venv/bin/python scripts/backfill_media_to_r2.py --dry-run
    .venv/bin/python scripts/backfill_media_to_r2.py
    .venv/bin/python scripts/backfill_media_to_r2.py --rewrite-log /path/to/log.jsonl

The R2 target and public base come from the ``R2_*`` settings (``app.config``);
the script fails fast with a clear message if they are unset (except under
``--dry-run``, which does not touch R2).
"""

import argparse
import json
import mimetypes
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path so we can import app modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import structlog

from app.config import get_settings
from app.database import close_db, get_db, init_db
from app.services import object_storage_service

logger = structlog.get_logger(__name__)

# Legacy static media lives under this URL prefix; on disk it maps to
# ``{static_file_path}/products/<filename>`` and to the R2 key ``products/<filename>``.
_STATIC_PREFIX = "/static/products/"
_R2_KEY_PREFIX = "products/"

_DEFAULT_REWRITE_LOG = "backfill_r2_rewrites.jsonl"

# The URL columns to migrate, per table. The row ``id`` is always selected too.
_TARGETS: dict[str, tuple[str, ...]] = {
    "product_images": ("image_url", "thumbnail_url", "zoom_url"),
    "product_videos": ("video_url", "poster_url"),
}


@dataclass
class Summary:
    """Aggregate counts for the run summary."""

    uploaded: int = 0
    skipped_already_r2: int = 0
    skipped_external: int = 0
    skipped_empty: int = 0
    missing_files: int = 0
    errors: int = 0
    missing_details: list[str] = field(default_factory=list)
    error_details: list[str] = field(default_factory=list)

    def render(self, *, dry_run: bool) -> str:
        mode = "DRY-RUN (no changes written)" if dry_run else "LIVE"
        lines = [
            f"Backfill summary [{mode}]",
            f"  uploaded/rewritten : {self.uploaded}",
            f"  skipped (already R2): {self.skipped_already_r2}",
            f"  skipped (external) : {self.skipped_external}",
            f"  skipped (empty)    : {self.skipped_empty}",
            f"  missing files      : {self.missing_files}",
            f"  errors             : {self.errors}",
        ]
        if self.missing_details:
            lines.append("  missing:")
            lines.extend(f"    - {detail}" for detail in self.missing_details)
        if self.error_details:
            lines.append("  errors:")
            lines.extend(f"    - {detail}" for detail in self.error_details)
        return "\n".join(lines)


def _content_type_for(filename: str) -> str:
    """Best-effort content type from the filename extension.

    Product media is only WebP (``image/webp``) and MP4 (``video/mp4``); fall
    back to a generic binary type for anything unexpected so the upload still
    carries a valid ``ContentType``.
    """
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _is_r2_url(url: str, public_base: str) -> bool:
    """True when ``url`` already points at the configured R2 public base."""
    if not public_base:
        return False
    prefix = public_base.rstrip("/") + "/"
    return url.startswith(prefix)


def _derive_key(static_url: str) -> str:
    """Map a ``/static/products/<filename>`` URL to its R2 key ``products/<filename>``.

    Rejects a filename carrying path separators or traversal so a malformed URL
    produces an explicit error rather than an unsafe key that escapes the
    ``products/`` prefix.
    """
    filename = static_url[len(_STATIC_PREFIX) :]
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        msg = f"Refusing to derive R2 key from unsafe static filename: {filename!r}"
        raise ValueError(msg)
    return _R2_KEY_PREFIX + filename


class _RewriteLog:
    """Append-only JSONL log of DB rewrites for rollback reverse-mapping."""

    def __init__(self, path: Path, *, enabled: bool) -> None:
        self._path = path
        self._enabled = enabled

    def record(self, *, table: str, row_id: str, column: str, old_url: str, new_url: str) -> None:
        if not self._enabled:
            return
        entry = {
            "recorded_at": datetime.now(UTC).isoformat(),
            "table": table,
            "row_id": row_id,
            "column": column,
            "old_url": old_url,
            "new_url": new_url,
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


def _process_url(
    *,
    table: str,
    row_id: str,
    column: str,
    url: str | None,
    static_products_root: Path,
    public_base: str,
    dry_run: bool,
    rewrite_log: _RewriteLog,
    summary: Summary,
) -> None:
    """Migrate a single URL column value for one row.

    Uploads the on-disk file to R2 and rewrites the DB column in its own
    committed transaction (unless ``--dry-run``). Classifies and counts skips
    (already-R2, external, empty) and non-fatal misses (missing file).
    """
    if not url:
        summary.skipped_empty += 1
        return

    if _is_r2_url(url, public_base):
        summary.skipped_already_r2 += 1
        return

    if not url.startswith(_STATIC_PREFIX):
        # Absolute external URL (e.g. CSV-imported) or a legacy shape we do not
        # own — leave it untouched.
        summary.skipped_external += 1
        logger.debug(
            "backfill_skip_external", table=table, row_id=row_id, column=column, url=url
        )
        return

    try:
        key = _derive_key(url)
    except ValueError as exc:
        summary.errors += 1
        summary.error_details.append(f"{table}#{row_id}.{column}: {exc}")
        logger.warning("backfill_bad_url", table=table, row_id=row_id, column=column, url=url)
        return

    filename = url[len(_STATIC_PREFIX) :]
    source_path = (static_products_root / filename).resolve()
    # Guard against a filename that escapes the products root.
    try:
        source_path.relative_to(static_products_root)
    except ValueError:
        summary.errors += 1
        summary.error_details.append(f"{table}#{row_id}.{column}: path escapes static root")
        return

    if not source_path.is_file():
        summary.missing_files += 1
        detail = f"{table}#{row_id}.{column}: {source_path}"
        summary.missing_details.append(detail)
        logger.warning(
            "backfill_missing_file",
            table=table,
            row_id=row_id,
            column=column,
            path=str(source_path),
        )
        return

    if dry_run:
        # Dry-run must not require R2 config. public_url() raises
        # StorageConfigError when R2_PUBLIC_BASE_URL is unset, so only resolve
        # the real URL when configured; otherwise log the target key alone.
        try:
            preview_url = object_storage_service.public_url(key)
        except object_storage_service.StorageConfigError:
            preview_url = None
        summary.uploaded += 1
        logger.info(
            "backfill_would_upload",
            table=table,
            row_id=row_id,
            column=column,
            key=key,
            new_url=preview_url,
        )
        return

    new_url = object_storage_service.public_url(key)

    try:
        data = source_path.read_bytes()
        object_storage_service.upload_bytes(key, data, _content_type_for(filename))
    except (OSError, object_storage_service.MediaStorageError) as exc:
        summary.errors += 1
        summary.error_details.append(f"{table}#{row_id}.{column}: {exc}")
        logger.warning(
            "backfill_upload_failed",
            table=table,
            row_id=row_id,
            column=column,
            key=key,
            error=str(exc),
        )
        return

    # Per-row commit: rewrite the single column, log it, then let the get_db()
    # context manager commit so an interruption never loses completed work.
    with get_db() as conn:
        conn.execute(
            f"UPDATE {table} SET {column} = %s WHERE id = %s",  # noqa: S608 - table/column are from a fixed allowlist.
            (new_url, row_id),
        )
    rewrite_log.record(
        table=table, row_id=row_id, column=column, old_url=url, new_url=new_url
    )
    summary.uploaded += 1
    logger.info(
        "backfill_uploaded", table=table, row_id=row_id, column=column, key=key, new_url=new_url
    )


def backfill(*, dry_run: bool, rewrite_log_path: Path) -> Summary:
    """Run the disk->R2 backfill across all target tables/columns."""
    settings = get_settings()
    public_base = settings.r2_public_base_url
    static_products_root = (Path(settings.static_file_path) / "products").resolve()

    if not dry_run and not public_base:
        msg = "R2 is not configured (R2_PUBLIC_BASE_URL is empty); cannot run a live backfill."
        raise object_storage_service.StorageConfigError(msg)

    summary = Summary()
    rewrite_log = _RewriteLog(rewrite_log_path, enabled=not dry_run)

    for table, columns in _TARGETS.items():
        select_cols = ", ".join(("id", *columns))
        with get_db() as conn:
            rows = conn.execute(
                f"SELECT {select_cols} FROM {table}"  # noqa: S608 - table/columns from a fixed allowlist.
            ).fetchall()

        for row in rows:
            for column in columns:
                _process_url(
                    table=table,
                    row_id=row["id"],
                    column=column,
                    url=row[column],
                    static_products_root=static_products_root,
                    public_base=public_base,
                    dry_run=dry_run,
                    rewrite_log=rewrite_log,
                    summary=summary,
                )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be uploaded/rewritten without touching R2 or the DB.",
    )
    parser.add_argument(
        "--rewrite-log",
        default=_DEFAULT_REWRITE_LOG,
        help=(
            "Path to the JSONL rewrite log (old->new URL) for rollback reverse-mapping. "
            f"Default: {_DEFAULT_REWRITE_LOG} (only written on a live run)."
        ),
    )
    args = parser.parse_args()

    init_db()
    try:
        summary = backfill(
            dry_run=args.dry_run,
            rewrite_log_path=Path(args.rewrite_log),
        )
    finally:
        close_db()

    print(summary.render(dry_run=args.dry_run))  # noqa: T201 - CLI summary output.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
