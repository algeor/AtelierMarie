"""Tests for low-level video validation and ffmpeg wrappers."""

import json
import subprocess

import pytest

from app.config import get_settings
from app.services import video_service


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


def test_transcode_uses_argument_list_and_static_output(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    settings = get_settings()
    monkeypatch.setattr(settings, "static_file_path", str(tmp_path / "static"))
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
    assert result["video_url"].startswith("/static/products/valid-product_")
    assert result["video_url"].endswith("_video.mp4")
