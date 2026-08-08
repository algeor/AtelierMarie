"""Tests for low-level video validation and ffmpeg wrappers."""

import json
import subprocess

import pytest

from app.config import get_settings
from app.services import object_storage_service, video_service


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
    backend = _FakeStorageBackend()
    object_storage_service.set_backend(backend)
    monkeypatch.setattr(
        get_settings(), "r2_public_base_url", "https://media.example.com", raising=False
    )
    yield backend
    object_storage_service.set_backend(None)


def test_probe_video_reads_duration_codec_and_dimensions(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")

    monkeypatch.setattr("app.services.video_service._resolve_binary", lambda binary, label: label)

    def fake_run(command, **kwargs):
        assert isinstance(command, list)
        assert kwargs["shell"] is False
        payload = {
            "streams": [{"codec_name": "h264", "width": 1920, "height": 1080}],
            "format": {"duration": "12.5"},
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert video_service.probe_video(source) == {
        "duration_secs": 12.5,
        "codec": "h264",
        "width": 1920,
        "height": 1080,
    }


def test_probe_video_maps_unreadable_file(tmp_path, monkeypatch):
    source = tmp_path / "broken.mp4"
    source.write_bytes(b"broken")
    monkeypatch.setattr("app.services.video_service._resolve_binary", lambda binary, label: label)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, stdout="", stderr="bad"),
    )

    with pytest.raises(video_service.InvalidVideoTypeError, match="file corrupted or unreadable"):
        video_service.probe_video(source)


def test_validate_video_upload_rejects_too_long(tmp_path, monkeypatch):
    source = tmp_path / "long.mp4"
    source.write_bytes(b"video")
    settings = get_settings()
    monkeypatch.setattr(settings, "max_video_duration_seconds", 30)
    monkeypatch.setattr(settings, "max_video_upload_bytes", 1024)
    monkeypatch.setattr("app.services.video_service._resolve_binary", lambda binary, label: label)
    monkeypatch.setattr(
        "app.services.video_service.probe_video",
        lambda source_path: {"duration_secs": 42.1, "codec": "h264", "width": 1920, "height": 1080},
    )

    with pytest.raises(video_service.VideoTooLongError, match="duration 42s exceeds 30s limit"):
        video_service.validate_video_upload(source, "valid-product")


def test_validate_video_upload_rejects_oversized_before_probe(tmp_path, monkeypatch):
    source = tmp_path / "large.mp4"
    source.write_bytes(b"x" * 11)
    settings = get_settings()
    monkeypatch.setattr(settings, "max_video_upload_bytes", 10)
    monkeypatch.setattr("app.services.video_service.probe_video", lambda source_path: pytest.fail())

    with pytest.raises(video_service.FileTooLargeError):
        video_service.validate_video_upload(source, "valid-product")


def test_validate_video_upload_reports_missing_ffmpeg(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    settings = get_settings()
    monkeypatch.setattr(settings, "max_video_upload_bytes", 1024)

    def missing(binary, label):
        if label == "ffmpeg":
            raise video_service.FfmpegUnavailableError("Video processing is unavailable")
        return label

    monkeypatch.setattr("app.services.video_service._resolve_binary", missing)

    with pytest.raises(video_service.FfmpegUnavailableError):
        video_service.validate_video_upload(source, "valid-product")


def test_unlink_video_files_allows_legacy_static_temp_source(tmp_path, monkeypatch):
    settings = get_settings()
    static_root = tmp_path / "static"
    current_temp = tmp_path / "video-temp"
    legacy_source = static_root / "video-temp" / "source.upload"
    legacy_source.parent.mkdir(parents=True)
    current_temp.mkdir()
    legacy_source.write_bytes(b"raw")
    monkeypatch.setattr(settings, "static_file_path", str(static_root))
    monkeypatch.setattr(settings, "video_upload_temp_path", str(current_temp))

    video_service.unlink_video_files(str(legacy_source))

    assert not legacy_source.exists()


def test_unlink_video_files_deletes_r2_objects_by_url(fake_storage, monkeypatch):
    video_service.unlink_video_files(
        "https://media.example.com/products/p_v_video.mp4",
        "https://media.example.com/products/p_v_poster.webp",
    )

    assert fake_storage.deleted == [
        "products/p_v_video.mp4",
        "products/p_v_poster.webp",
    ]


def test_unlink_video_files_skips_external_urls(fake_storage):
    video_service.unlink_video_files("https://cdn.other-host.example/legacy/clip.mp4")

    assert fake_storage.deleted == []


def test_unlink_video_files_r2_delete_error_is_swallowed(fake_storage, monkeypatch):
    def boom(key):
        raise object_storage_service.MediaStorageError("R2 down")

    monkeypatch.setattr(object_storage_service, "delete_object", boom)

    # Best-effort: a storage error must not propagate out of cleanup.
    video_service.unlink_video_files("https://media.example.com/products/p_v_video.mp4")


def test_video_product_id_validator_matches_create_model_slug_pattern():
    video_service.validate_product_id("x")


def test_transcode_uses_argument_list_and_local_output(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    settings = get_settings()
    monkeypatch.setattr(settings, "video_upload_temp_path", str(tmp_path / "video-temp"))
    monkeypatch.setattr("app.services.video_service._resolve_binary", lambda binary, label: label)
    monkeypatch.setattr("app.services.video_service._command_prefix", lambda: [])

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["shell"] = kwargs["shell"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = video_service.transcode(source, "valid-product", "a" * 32)

    assert captured["shell"] is False
    assert isinstance(captured["command"], list)
    assert result["video_path"].endswith("valid-product_" + "a" * 32 + "_video.mp4")
    assert "video-temp" in result["video_path"]
