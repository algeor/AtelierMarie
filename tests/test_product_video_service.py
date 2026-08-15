"""Tests for product video orchestration and response exposure."""

import concurrent.futures
import threading
from pathlib import Path

import pytest

from app.database import get_db
from app.services import (
    object_storage_service,
    product_service,
    product_video_service,
    video_service,
)


class _FakeStorageBackend:
    """In-memory key->bytes backend (design Decision 8); records deletes."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)


@pytest.fixture()
def fake_storage(monkeypatch):
    from app.config import get_settings

    backend = _FakeStorageBackend()
    object_storage_service.set_backend(backend)
    monkeypatch.setattr(
        get_settings(), "r2_public_base_url", "https://media.example.com", raising=False
    )
    yield backend
    object_storage_service.set_backend(None)


def _stage_transcode(product_id, video_id):
    """Write a staged MP4 to the computed local output path and return it."""
    video_path, _poster_path = video_service.output_paths(product_id, video_id)
    video_path.write_bytes(b"mp4-bytes")
    return {"video_path": str(video_path)}


def _stage_poster(product_id, video_id):
    """Write a staged poster to the computed local output path and return it."""
    _video_path, poster_path = video_service.output_paths(product_id, video_id)
    poster_path.write_bytes(b"webp-bytes")
    return {"poster_path": str(poster_path)}


def _patch_ffmpeg_staging(monkeypatch, *, transcode=None, poster=None):
    """Patch transcode/extract_poster to write staged local outputs (defaults)."""
    monkeypatch.setattr(
        "app.services.video_service.transcode",
        transcode or (lambda s, p, v: _stage_transcode(p, v)),
    )
    monkeypatch.setattr(
        "app.services.video_service.extract_poster",
        poster or (lambda s, p, v: _stage_poster(p, v)),
    )


@pytest.fixture()
def _video_product(db, tmp_path, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "static_file_path", str(tmp_path / "static"))
    monkeypatch.setattr(settings, "video_upload_temp_path", str(tmp_path / "video-temp"))
    product_service.create_product(
        {"id": "video-product", "name_en": "Video Product", "price_cents": 1000, "stock": 3}
    )
    return tmp_path


def test_public_response_exposes_ready_video_only(_video_product):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (
                id, product_id, status, video_url, poster_url, duration_secs, sort_order
            ) VALUES (
                'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'video-product', 'queued',
                NULL, NULL, 12.0, 1
            )
            """
        )

    assert product_service.get_product("video-product")["video"] is None

    with get_db() as conn:
        conn.execute(
            """
            UPDATE product_videos
            SET status = 'ready', video_url = '/static/products/video.mp4',
                poster_url = '/static/products/poster.webp'
            WHERE product_id = 'video-product'
            """
        )

    video = product_service.get_product("video-product")["video"]
    assert video["video_url"] == "/static/products/video.mp4"
    assert video["sort_order"] == 1


def test_queue_rejects_reupload_while_processing(_video_product, monkeypatch):
    monkeypatch.setattr(
        "app.services.video_service.validate_video_upload",
        lambda source_path, product_id: {"duration_secs": 10.0},
    )
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (
                'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'video-product', 'queued',
                '/tmp/source.mp4', 10.0
            )
            """
        )

    with pytest.raises(product_video_service.ProductVideoProcessingConflictError):
        product_video_service.queue_video_upload("video-product", b"fake-video")

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM product_videos").fetchone()["count"]
    assert count == 1


def test_queue_checks_product_before_probe(_video_product, monkeypatch):
    def fail_validate(source_path, product_id):
        raise AssertionError("ffprobe should not run for a missing product")

    monkeypatch.setattr("app.services.video_service.validate_video_upload", fail_validate)

    with pytest.raises(product_video_service.ProductNotFoundError):
        product_video_service.queue_video_upload("missing-product", b"fake-video")

    assert not Path(_video_product / "video-temp").exists()


def test_queue_path_rejects_processing_before_probe(_video_product, monkeypatch):
    def fail_validate(source_path, product_id):
        raise AssertionError("ffprobe should not run while a video is processing")

    monkeypatch.setattr("app.services.video_service.validate_video_upload", fail_validate)
    temp_path = product_video_service.reserve_temp_upload(
        "video-product", video_id="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    )
    temp_path.write_bytes(b"fake-video")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (
                'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'video-product', 'queued',
                '/tmp/source.mp4', 10.0
            )
            """
        )

    with pytest.raises(product_video_service.ProductVideoProcessingConflictError):
        product_video_service.queue_video_upload_path("video-product", temp_path)

    assert not temp_path.exists()


def test_queue_rejects_invalid_product_id_before_temp_write(_video_product):
    with pytest.raises(video_service.InvalidProductIdError):
        product_video_service.queue_video_upload("../bad", b"fake-video")

    assert not Path(_video_product / "video-temp").exists()


def test_replace_ready_video_unlinks_old_files(_video_product, monkeypatch):
    deleted: list[str | None] = []
    monkeypatch.setattr(
        "app.services.video_service.validate_video_upload",
        lambda source_path, product_id: {"duration_secs": 8.0},
    )
    monkeypatch.setattr(
        "app.services.video_service.unlink_video_files",
        lambda *items: deleted.extend(items),
    )
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (
                id, product_id, status, video_url, poster_url, source_path, duration_secs
            ) VALUES (
                'cccccccccccccccccccccccccccccccc', 'video-product', 'ready',
                '/static/products/old.mp4', '/static/products/old.webp', NULL, 8.0
            )
            """
        )

    video = product_video_service.queue_video_upload("video-product", b"fake-video")

    assert video["status"] == "queued"
    assert "/static/products/old.mp4" in deleted
    assert "/static/products/old.webp" in deleted


def test_drain_video_transcodes_success(_video_product, fake_storage, monkeypatch):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")
    _patch_ffmpeg_staging(monkeypatch)

    video_id = "dddddddddddddddddddddddddddddddd"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            (video_id, str(source)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    video_key = f"products/video-product_{video_id}_video.mp4"
    poster_key = f"products/video-product_{video_id}_poster.webp"
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM product_videos WHERE product_id = 'video-product'"
        ).fetchone()
    assert row["status"] == "ready"
    assert row["video_url"] == f"https://media.example.com/{video_key}"
    assert row["poster_url"] == f"https://media.example.com/{poster_key}"
    assert row["source_path"] is None
    # Durable copies are in R2; the raw source and staged outputs are gone.
    assert video_key in fake_storage.objects
    assert poster_key in fake_storage.objects
    assert not source.exists()
    staged_video, staged_poster = video_service.output_paths("video-product", video_id)
    assert not staged_video.exists()
    assert not staged_poster.exists()


def test_drain_video_transcodes_keeps_ready_when_poster_has_no_fallback(
    _video_product, fake_storage, monkeypatch
):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")

    def fail_poster(source_path, product_id, video_id):
        raise video_service.VideoProcessingError("poster failed")

    _patch_ffmpeg_staging(monkeypatch, poster=fail_poster)

    video_id = "abababababababababababababababab"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            (video_id, str(source)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        row = conn.execute("SELECT status, video_url, poster_url FROM product_videos").fetchone()
    assert row["status"] == "ready"
    assert (
        row["video_url"] == f"https://media.example.com/products/video-product_{video_id}_video.mp4"
    )
    assert row["poster_url"] is None


def test_drain_video_transcodes_poster_fallback_uses_primary_thumbnail(
    _video_product, fake_storage, monkeypatch
):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")

    def fail_poster(source_path, product_id, video_id):
        raise video_service.VideoProcessingError("poster failed")

    _patch_ffmpeg_staging(monkeypatch, poster=fail_poster)

    thumb_url = "https://media.example.com/products/video-product_img_thumb.webp"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_images (
                id, product_id, image_url, thumbnail_url, is_primary, sort_order
            ) VALUES (
                'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'video-product',
                'https://media.example.com/products/video-product_img.webp', %s, 1, 0
            )
            """,
            (thumb_url,),
        )
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES ('bcbcbcbcbcbcbcbcbcbcbcbcbcbcbcbc', 'video-product', 'queued', %s, 8.0)
            """,
            (str(source),),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        row = conn.execute("SELECT status, poster_url FROM product_videos").fetchone()
    assert row["status"] == "ready"
    # Poster falls back to the primary thumbnail (already an R2 URL post-migration).
    assert row["poster_url"] == thumb_url


def test_drain_video_transcodes_does_not_overwrite_row_no_longer_transcoding(
    _video_product, fake_storage, monkeypatch
):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")

    def transcode(source_path, product_id, video_id):
        with get_db() as conn:
            conn.execute(
                """
                UPDATE product_videos
                SET status = 'failed', failure_reason = 'lease stolen'
                WHERE id = %s
                """,
                (video_id,),
            )
        return _stage_transcode(product_id, video_id)

    _patch_ffmpeg_staging(monkeypatch, transcode=transcode)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            ("cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd", str(source)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        row = conn.execute(
            "SELECT status, failure_reason, video_url FROM product_videos"
        ).fetchone()
    assert row["status"] == "failed"
    assert row["failure_reason"] == "lease stolen"
    assert row["video_url"] is None


def test_drain_processes_only_one_queued_video_per_sweep(_video_product, fake_storage, monkeypatch):
    from app.services import product_service

    product_service.create_product(
        {"id": "second-video-product", "name_en": "Second", "price_cents": 1000, "stock": 3}
    )
    source_one = Path(_video_product / "video-temp" / "one.upload")
    source_two = Path(_video_product / "video-temp" / "two.upload")
    source_one.parent.mkdir(parents=True, exist_ok=True)
    source_one.write_bytes(b"one")
    source_two.write_bytes(b"two")
    _patch_ffmpeg_staging(monkeypatch)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            ("11111111111111111111111111111111", str(source_one)),
        )
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'second-video-product', 'queued', %s, 8.0)
            """,
            ("22222222222222222222222222222222", str(source_two)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM product_videos GROUP BY status"
        ).fetchall()
    assert {row["status"]: row["count"] for row in rows} == {"queued": 1, "ready": 1}


def test_concurrent_drains_only_one_claims_single_queued_video(
    _video_product, fake_storage, monkeypatch
):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")
    claimed = threading.Event()
    release = threading.Event()

    def transcode(source_path, product_id, video_id):
        claimed.set()
        assert release.wait(timeout=5)
        return _stage_transcode(product_id, video_id)

    _patch_ffmpeg_staging(monkeypatch, transcode=transcode)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            ("33333333333333333333333333333333", str(source)),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(product_video_service.drain_video_transcodes)
        assert claimed.wait(timeout=5)
        second = executor.submit(product_video_service.drain_video_transcodes)
        assert second.result(timeout=5) == 0
        release.set()
        assert first.result(timeout=5) == 1

    with get_db() as conn:
        row = conn.execute("SELECT status FROM product_videos").fetchone()
    assert row["status"] == "ready"


def test_drain_video_transcodes_failure_is_terminal(_video_product, monkeypatch):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")

    def fail_transcode(source_path, product_id, video_id):
        msg = "transcode failed: bad source"
        raise RuntimeError(msg)

    monkeypatch.setattr("app.services.video_service.transcode", fail_transcode)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            ("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", str(source)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        row = conn.execute(
            "SELECT status, failure_reason, source_path FROM product_videos"
        ).fetchone()
    assert row["status"] == "failed"
    assert row["failure_reason"] == "transcode failed: bad source"
    assert row["source_path"] is None


def test_drain_video_transcodes_r2_upload_failure_does_not_go_ready(
    _video_product, fake_storage, monkeypatch
):
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")
    _patch_ffmpeg_staging(monkeypatch)

    def boom(key, data, content_type):
        raise object_storage_service.MediaStorageError("R2 upload failed")

    monkeypatch.setattr(object_storage_service, "upload_bytes", boom)

    video_id = "aeaeaeaeaeaeaeaeaeaeaeaeaeaeaeae"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            (video_id, str(source)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        row = conn.execute(
            "SELECT status, video_url, poster_url, source_path FROM product_videos"
        ).fetchone()
    assert row["status"] == "failed"
    assert row["video_url"] is None
    assert row["poster_url"] is None
    assert row["source_path"] is None
    # Staged local outputs are cleaned up on the failure path.
    staged_video, staged_poster = video_service.output_paths("video-product", video_id)
    assert not staged_video.exists()
    assert not staged_poster.exists()
    assert not source.exists()


def test_drain_video_transcodes_poster_upload_failure_deletes_orphaned_mp4(
    _video_product, fake_storage, monkeypatch
):
    """MP4 lands in R2, then the poster upload fails: the MP4 must be deleted
    (no ready transition, nothing orphaned in the bucket)."""
    source = Path(_video_product / "video-temp" / "source.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake")
    _patch_ffmpeg_staging(monkeypatch)

    real_put = fake_storage.put_object

    def put_fail_on_poster(key, data, content_type):
        if content_type == "image/webp":
            raise object_storage_service.MediaStorageError("poster upload failed")
        real_put(key, data, content_type)

    monkeypatch.setattr(fake_storage, "put_object", put_fail_on_poster)

    video_id = "bebebebebebebebebebebebebebebebe"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (%s, 'video-product', 'queued', %s, 8.0)
            """,
            (video_id, str(source)),
        )

    assert product_video_service.drain_video_transcodes() == 1

    video_key = object_storage_service.object_key_for_video("video-product", video_id)
    # The MP4 was uploaded then compensated-deleted; nothing durable remains.
    assert video_key in fake_storage.deleted
    assert video_key not in fake_storage.objects

    with get_db() as conn:
        row = conn.execute("SELECT status, video_url, poster_url FROM product_videos").fetchone()
    assert row["status"] == "failed"
    assert row["video_url"] is None
    assert row["poster_url"] is None


def test_expired_transcode_marked_failed(_video_product):
    source = Path(_video_product / "video-temp" / "expired.upload")
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"raw")
    # Staged transcode outputs now live in the local temp dir, not /static.
    partial = Path(
        _video_product / "video-temp" / "video-product_ffffffffffffffffffffffffffffffff_video.mp4"
    )
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(b"partial")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (
                id, product_id, status, source_path, duration_secs, lease_expires_at
            ) VALUES (
                'ffffffffffffffffffffffffffffffff', 'video-product', 'transcoding',
                %s, 8.0, '2000-01-01 00:00:00'
            )
            """,
            (str(source),),
        )

    assert product_video_service.drain_video_transcodes() == 1

    with get_db() as conn:
        row = conn.execute(
            "SELECT status, failure_reason, source_path FROM product_videos"
        ).fetchone()
    assert row["status"] == "failed"
    assert row["failure_reason"] == "processing interrupted"
    assert row["source_path"] is None
    assert not source.exists()
    assert not partial.exists()


def test_delete_transcoding_video_removes_row(_video_product):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (
                '12121212121212121212121212121212', 'video-product', 'transcoding',
                '/tmp/source.upload', 8.0
            )
            """
        )

    product_video_service.delete_video("video-product")

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM product_videos").fetchone()["count"]
    assert count == 0


def test_product_deactivate_removes_transcoding_video_and_soft_deletes(_video_product):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (id, product_id, status, source_path, duration_secs)
            VALUES (
                '34343434343434343434343434343434', 'video-product', 'transcoding',
                '/tmp/source.upload', 8.0
            )
            """
        )

    product = product_service.deactivate_product("video-product")

    with get_db() as conn:
        stored_product = conn.execute(
            "SELECT is_active FROM products WHERE id = 'video-product'"
        ).fetchone()
        video = conn.execute(
            "SELECT status FROM product_videos WHERE product_id = %s", ("video-product",)
        ).fetchone()
    assert product["is_active"] == 0
    assert stored_product["is_active"] == 0
    assert product["video"] is None
    assert video is None


def test_delete_video_unlinks_files(_video_product, monkeypatch):
    deleted: list[str | None] = []
    monkeypatch.setattr(
        "app.services.video_service.unlink_video_files",
        lambda *items: deleted.extend(items),
    )
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (
                id, product_id, status, video_url, poster_url, source_path, duration_secs
            ) VALUES (
                '44444444444444444444444444444444', 'video-product', 'ready',
                '/static/products/video.mp4', '/static/products/poster.webp',
                '/tmp/source.upload', 8.0
            )
            """
        )

    product_video_service.delete_video("video-product")

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM product_videos").fetchone()["count"]
    assert count == 0
    assert deleted == [
        "/static/products/video.mp4",
        "/static/products/poster.webp",
        "/tmp/source.upload",
    ]


def test_product_deactivate_removes_video_row_and_unlinks_files(_video_product, monkeypatch):
    deleted: list[str | None] = []
    monkeypatch.setattr(
        "app.services.video_service.unlink_video_files",
        lambda *items: deleted.extend(items),
    )
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_videos (
                id, product_id, status, video_url, poster_url, source_path, duration_secs
            ) VALUES (
                '55555555555555555555555555555555', 'video-product', 'ready',
                '/static/products/video.mp4', '/static/products/poster.webp', NULL, 8.0
            )
            """
        )

    product = product_service.deactivate_product("video-product")

    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM product_videos").fetchone()["count"]
    assert product["is_active"] == 0
    assert product["video"] is None
    assert count == 0
    assert "/static/products/video.mp4" in deleted
    assert "/static/products/poster.webp" in deleted
