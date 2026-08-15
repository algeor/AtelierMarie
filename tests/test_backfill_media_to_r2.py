"""Tests for the disk->R2 media backfill script (scripts/backfill_media_to_r2.py).

Exercises the four properties the design requires (Decision 6 / Task 8.8):

- ``--dry-run`` uploads nothing and rewrites no DB rows,
- a live run is idempotent (a re-run skips rows already on the R2 public base),
- a missing on-disk source file is reported and non-fatal (the run continues),
- external absolute URLs (CSV-imported) are left untouched.

The object store is the in-memory fake backend (``fake_storage`` fixture) — no
live bucket, no credentials. The DB is the per-worker Postgres provisioned by the
root conftest; ``static_file_path`` is redirected to a tmp dir so the "on-disk"
source files are real files the script can read.
"""

import importlib

import pytest

from app.config import get_settings
from app.database import get_db
from app.services import product_service

backfill_module = importlib.import_module("scripts.backfill_media_to_r2")

_R2_PUBLIC_BASE = "https://cdn.test.example"


@pytest.fixture()
def static_root(tmp_path, monkeypatch, db):
    """Redirect ``static_file_path`` to a tmp dir and return the products root.

    Depends on ``db`` so the psycopg pool is initialized (``app`` fixture) before
    the backfill runs ``get_db()``.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "static_file_path", str(tmp_path))
    products_dir = tmp_path / "products"
    products_dir.mkdir(parents=True, exist_ok=True)
    return products_dir


@pytest.fixture()
def seeded_image(fake_storage, static_root):
    """Seed one product + one image row with /static URLs and on-disk files.

    Returns the image id and the three (column, filename, static_url) tuples so
    tests can assert what got uploaded/rewritten.
    """
    product_service.create_product(
        {"id": "backfill-prod", "name_en": "Backfill", "price_cents": 1000, "stock": 1}
    )
    image_id = "a" * 32
    variants = {
        "image_url": f"backfill-prod_{image_id}.webp",
        "thumbnail_url": f"backfill-prod_{image_id}_thumb.webp",
        "zoom_url": f"backfill-prod_{image_id}_zoom.webp",
    }
    for filename in variants.values():
        (static_root / filename).write_bytes(b"webp-bytes-" + filename.encode())

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
            ) VALUES (%s, %s, %s, %s, %s, 0, 1)
            """,
            (
                image_id,
                "backfill-prod",
                f"/static/products/{variants['image_url']}",
                f"/static/products/{variants['thumbnail_url']}",
                f"/static/products/{variants['zoom_url']}",
            ),
        )
    return image_id, variants


def _image_row(image_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT image_url, thumbnail_url, zoom_url FROM product_images WHERE id = %s",
            (image_id,),
        ).fetchone()
    return dict(row)


def test_dry_run_makes_no_changes(seeded_image, fake_storage, tmp_path):
    image_id, _variants = seeded_image
    log_path = tmp_path / "rewrites.jsonl"

    summary = backfill_module.backfill(dry_run=True, rewrite_log_path=log_path)

    # Reports what it would do, but uploads nothing and rewrites no DB rows.
    assert summary.uploaded == 3
    assert fake_storage.objects == {}
    assert not log_path.exists()
    row = _image_row(image_id)
    assert row["image_url"].startswith("/static/products/")
    assert row["thumbnail_url"].startswith("/static/products/")
    assert row["zoom_url"].startswith("/static/products/")


def test_dry_run_needs_no_r2_config(seeded_image, static_root, tmp_path, monkeypatch):
    """Dry-run must not require R2 config (the script doc says it never touches R2).

    With ``R2_PUBLIC_BASE_URL`` unset, public_url() raises StorageConfigError; a
    dry-run must still succeed (it only reports would-be uploads, no real URL).
    """
    from app.services import object_storage_service

    image_id, _variants = seeded_image
    # Reset any injected backend and clear the public base so public_url() would
    # raise if the dry-run path tried to resolve a real URL.
    object_storage_service.set_backend(None)
    settings = get_settings()
    monkeypatch.setattr(settings, "r2_public_base_url", "", raising=False)
    log_path = tmp_path / "rewrites.jsonl"

    summary = backfill_module.backfill(dry_run=True, rewrite_log_path=log_path)

    assert summary.uploaded == 3
    assert summary.errors == 0
    assert not log_path.exists()
    row = _image_row(image_id)
    assert row["image_url"].startswith("/static/products/")


def test_live_run_uploads_and_rewrites(seeded_image, fake_storage, tmp_path):
    image_id, variants = seeded_image
    log_path = tmp_path / "rewrites.jsonl"

    summary = backfill_module.backfill(dry_run=False, rewrite_log_path=log_path)

    assert summary.uploaded == 3
    # Objects landed in R2 under products/<stem> keys and DB rows now point at R2.
    for filename in variants.values():
        assert f"products/{filename}" in fake_storage.objects
    row = _image_row(image_id)
    assert row["image_url"] == f"{_R2_PUBLIC_BASE}/products/{variants['image_url']}"
    assert row["zoom_url"] == f"{_R2_PUBLIC_BASE}/products/{variants['zoom_url']}"
    # A rewrite log was written for rollback reverse-mapping.
    assert log_path.exists()
    assert log_path.read_text().count("\n") == 3


def test_re_run_is_idempotent(seeded_image, fake_storage, tmp_path):
    image_id, _variants = seeded_image
    log_path = tmp_path / "rewrites.jsonl"

    backfill_module.backfill(dry_run=False, rewrite_log_path=log_path)
    row_after_first = _image_row(image_id)

    # Second run: every row already points at R2, so nothing is uploaded/rewritten.
    summary = backfill_module.backfill(dry_run=False, rewrite_log_path=log_path)

    assert summary.uploaded == 0
    assert summary.skipped_already_r2 == 3
    assert _image_row(image_id) == row_after_first


def test_missing_source_file_is_reported_not_fatal(fake_storage, static_root, tmp_path):
    """A /static URL whose file is absent is counted and skipped; the run continues."""
    product_service.create_product(
        {"id": "missing-prod", "name_en": "Missing", "price_cents": 1000, "stock": 1}
    )
    image_id = "b" * 32
    present = f"missing-prod_{image_id}.webp"
    (static_root / present).write_bytes(b"present")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
            ) VALUES (%s, %s, %s, %s, %s, 0, 1)
            """,
            (
                image_id,
                "missing-prod",
                f"/static/products/{present}",
                f"/static/products/missing-prod_{image_id}_thumb.webp",  # no file on disk
                None,
            ),
        )

    summary = backfill_module.backfill(dry_run=False, rewrite_log_path=tmp_path / "log.jsonl")

    # The present file uploaded; the missing thumbnail is reported, not fatal.
    assert summary.uploaded == 1
    assert summary.missing_files == 1
    assert f"products/{present}" in fake_storage.objects
    row = _image_row(image_id)
    assert row["image_url"] == f"{_R2_PUBLIC_BASE}/products/{present}"
    # The missing-file column was left untouched (still /static).
    assert row["thumbnail_url"].startswith("/static/products/")


def test_external_urls_are_untouched(fake_storage, static_root, tmp_path):
    """Absolute external URLs (CSV-imported) are skipped and never rewritten."""
    product_service.create_product(
        {"id": "external-prod", "name_en": "External", "price_cents": 1000, "stock": 1}
    )
    image_id = "c" * 32
    external_main = "https://images.other-cdn.example/legacy/photo.jpg"
    external_thumb = "https://images.other-cdn.example/legacy/photo_thumb.jpg"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, zoom_url, sort_order, is_primary
            ) VALUES (%s, %s, %s, %s, %s, 0, 1)
            """,
            (image_id, "external-prod", external_main, external_thumb, None),
        )

    summary = backfill_module.backfill(dry_run=False, rewrite_log_path=tmp_path / "log.jsonl")

    assert summary.uploaded == 0
    assert summary.skipped_external == 2
    assert fake_storage.objects == {}
    row = _image_row(image_id)
    assert row["image_url"] == external_main
    assert row["thumbnail_url"] == external_thumb


def test_derived_about_and_home_images_upload_without_db_rewrites(
    fake_storage, static_root, tmp_path
):
    about_image_id = "d" * 32
    home_image_id = "e" * 32
    about_filename = f"about-hero_{about_image_id}.webp"
    (static_root / about_filename).write_bytes(b"about-hero")

    with get_db() as conn:
        home_item_id = conn.execute(
            "SELECT id FROM home_items ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        conn.execute(
            "UPDATE about_sections SET image_id = %s WHERE slug = 'hero'",
            (about_image_id,),
        )
        conn.execute(
            "UPDATE home_items SET image_id = %s WHERE id = %s",
            (home_image_id, home_item_id),
        )

    home_filename = f"home-item-{home_item_id}_{home_image_id}.webp"
    (static_root / home_filename).write_bytes(b"home-item")

    summary = backfill_module.backfill(dry_run=False, rewrite_log_path=tmp_path / "log.jsonl")

    assert summary.uploaded == 2
    assert f"products/{about_filename}" in fake_storage.objects
    assert f"products/{home_filename}" in fake_storage.objects


def test_force_reuploads_site_media_rows_already_pointing_at_r2(
    fake_storage, static_root, tmp_path
):
    image_id = "f" * 32
    variants = {
        "image_url": f"site-media-home-hero_{image_id}.webp",
        "thumbnail_url": f"site-media-home-hero_{image_id}_thumb.webp",
        "zoom_url": f"site-media-home-hero_{image_id}_zoom.webp",
    }
    for filename in variants.values():
        (static_root / filename).write_bytes(b"site-media-" + filename.encode())

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO site_media_assets (key, image_id, image_url, thumbnail_url, zoom_url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE
            SET image_id = EXCLUDED.image_id,
                image_url = EXCLUDED.image_url,
                thumbnail_url = EXCLUDED.thumbnail_url,
                zoom_url = EXCLUDED.zoom_url
            """,
            (
                "home_hero",
                image_id,
                f"{_R2_PUBLIC_BASE}/products/{variants['image_url']}",
                f"{_R2_PUBLIC_BASE}/products/{variants['thumbnail_url']}",
                f"{_R2_PUBLIC_BASE}/products/{variants['zoom_url']}",
            ),
        )

    summary = backfill_module.backfill(
        dry_run=False,
        rewrite_log_path=tmp_path / "log.jsonl",
        force=True,
    )

    assert summary.uploaded == 3
    for filename in variants.values():
        assert f"products/{filename}" in fake_storage.objects

    with get_db() as conn:
        row = conn.execute(
            "SELECT image_url, thumbnail_url, zoom_url FROM site_media_assets "
            "WHERE key = 'home_hero'"
        ).fetchone()

    assert row["image_url"] == f"{_R2_PUBLIC_BASE}/products/{variants['image_url']}"
    assert row["thumbnail_url"] == f"{_R2_PUBLIC_BASE}/products/{variants['thumbnail_url']}"
    assert row["zoom_url"] == f"{_R2_PUBLIC_BASE}/products/{variants['zoom_url']}"
