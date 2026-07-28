"""Video service — validation, transcoding, poster extraction, and cleanup."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import structlog

from app.config import get_settings
from app.constants import (
    VIDEO_FFMPEG_IONICE_CLASS,
    VIDEO_FFMPEG_IONICE_LEVEL,
    VIDEO_FFMPEG_NICE_LEVEL,
    VIDEO_FFMPEG_TIMEOUT_SECONDS,
    VIDEO_FFPROBE_TIMEOUT_SECONDS,
    VIDEO_POSTER_TIMESTAMP_SECONDS,
    VIDEO_TRANSCODE_ARGS,
)
from app.models.common import PRODUCT_ID_PATTERN

logger = structlog.get_logger(__name__)

_SLUG_RE = re.compile(PRODUCT_ID_PATTERN)
_VIDEO_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "mpeg4", "vp8", "vp9", "av1"}


class VideoServiceError(Exception):
    """Base for all video service errors."""


class InvalidVideoTypeError(VideoServiceError):
    """File is not a readable or supported video."""


class VideoTooLongError(VideoServiceError):
    """Video duration exceeds the configured maximum."""


class FileTooLargeError(VideoServiceError):
    """File exceeds the maximum allowed size."""


class VideoProcessingError(VideoServiceError):
    """Video could not be processed."""


class FfmpegUnavailableError(VideoServiceError):
    """ffmpeg or ffprobe is not available on this host."""


class InvalidProductIdError(VideoServiceError):
    """Product ID does not match the required slug format."""


class InvalidVideoIdError(VideoServiceError):
    """Video ID does not match the required UUID hex format."""


def _resolve_binary(binary: str, label: str) -> str:
    path = Path(binary)
    if path.is_absolute():
        if path.exists() and path.is_file():
            return str(path)
        raise FfmpegUnavailableError(f"{label} is unavailable at {binary}")
    resolved = shutil.which(binary)
    if resolved is None:
        raise FfmpegUnavailableError(
            f"Video processing is unavailable because {label} is not installed"
        )
    return resolved


def _validate_product_id(product_id: str) -> None:
    if not product_id or not _SLUG_RE.match(product_id):
        raise InvalidProductIdError(
            "Product ID must be a valid slug (lowercase alphanumeric + hyphens)"
        )


def validate_product_id(product_id: str) -> None:
    """Validate a product slug before using it in filesystem paths."""
    _validate_product_id(product_id)


def _validate_video_id(video_id: str) -> None:
    if not video_id or not _VIDEO_ID_RE.match(video_id):
        raise InvalidVideoIdError("Video ID must be a UUID hex string")


def validate_video_id(video_id: str) -> None:
    """Validate a video UUID hex before using it in filesystem paths."""
    _validate_video_id(video_id)


def _static_products_dir(static_path: str | None = None) -> Path:
    settings = get_settings()
    base = Path(static_path or settings.static_file_path).resolve()
    products_dir = (base / "products").resolve()
    products_dir.mkdir(parents=True, exist_ok=True)
    return products_dir


def _output_paths(
    product_id: str, video_id: str, static_path: str | None = None
) -> tuple[Path, Path]:
    _validate_product_id(product_id)
    _validate_video_id(video_id)
    products_dir = _static_products_dir(static_path)
    stem = f"{product_id}_{video_id}"
    video_path = (products_dir / f"{stem}_video.mp4").resolve()
    poster_path = (products_dir / f"{stem}_poster.webp").resolve()
    try:
        video_path.relative_to(products_dir)
        poster_path.relative_to(products_dir)
    except ValueError as exc:
        raise VideoProcessingError("Path traversal detected") from exc
    return video_path, poster_path


def _command_prefix() -> list[str]:
    prefix: list[str] = []
    nice = shutil.which("nice")
    ionice = shutil.which("ionice")
    if nice is not None:
        prefix.extend([nice, "-n", VIDEO_FFMPEG_NICE_LEVEL])
    if ionice is not None:
        prefix.extend(
            [
                ionice,
                "-c",
                VIDEO_FFMPEG_IONICE_CLASS,
                "-n",
                VIDEO_FFMPEG_IONICE_LEVEL,
            ]
        )
    return prefix


def _stderr_tail(result: subprocess.CompletedProcess[str]) -> str:
    stderr = (result.stderr or "").strip()
    if not stderr:
        return "unknown ffmpeg error"
    return stderr[-500:]


def probe_video(source_path: str | Path) -> dict:
    """Probe a source video with ffprobe and return duration/codec/dimensions."""
    settings = get_settings()
    ffprobe = _resolve_binary(settings.ffprobe_path, "ffprobe")
    source = Path(source_path).resolve()
    if not source.exists() or not source.is_file():
        raise InvalidVideoTypeError("file corrupted or unreadable")

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height,duration:format=duration",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=VIDEO_FFPROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise InvalidVideoTypeError("file corrupted or unreadable") from exc

    if result.returncode != 0:
        raise InvalidVideoTypeError("file corrupted or unreadable")

    try:
        payload = json.loads(result.stdout or "{}")
        stream = (payload.get("streams") or [])[0]
        duration_raw = stream.get("duration") or payload.get("format", {}).get("duration")
        duration = float(duration_raw)
        codec = str(stream["codec_name"])
        width = int(stream["width"])
        height = int(stream["height"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise InvalidVideoTypeError("file corrupted or unreadable") from exc

    if codec not in _SUPPORTED_VIDEO_CODECS:
        raise InvalidVideoTypeError("unsupported source codec")
    return {"duration_secs": duration, "codec": codec, "width": width, "height": height}


def validate_video_upload(source_path: str | Path, product_id: str) -> dict:
    """Validate product slug, upload size, ffmpeg availability, and duration."""
    settings = get_settings()
    _validate_product_id(product_id)
    source = Path(source_path).resolve()
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise InvalidVideoTypeError("file corrupted or unreadable") from exc
    if size > settings.max_video_upload_bytes:
        raise FileTooLargeError(
            f"File size exceeds maximum of {settings.max_video_upload_bytes} bytes"
        )
    _resolve_binary(settings.ffmpeg_path, "ffmpeg")
    probe = probe_video(source)
    max_duration = settings.max_video_duration_seconds
    if probe["duration_secs"] > max_duration:
        duration = int(round(probe["duration_secs"]))
        raise VideoTooLongError(f"duration {duration}s exceeds {max_duration}s limit")
    return probe


def transcode(source_path: str | Path, product_id: str, video_id: str) -> dict:
    """Transcode a validated source into normalized browser-compatible MP4."""
    settings = get_settings()
    ffmpeg = _resolve_binary(settings.ffmpeg_path, "ffmpeg")
    source = Path(source_path).resolve()
    output_path, _poster_path = _output_paths(product_id, video_id)
    command = [
        *_command_prefix(),
        ffmpeg,
        "-y",
        "-i",
        str(source),
        *VIDEO_TRANSCODE_ARGS,
        str(output_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=VIDEO_FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise VideoProcessingError("transcode timed out") from exc
    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise VideoProcessingError(f"transcode failed: {_stderr_tail(result)}")
    return {"video_url": f"/static/products/{output_path.name}"}


def extract_poster(source_path: str | Path, product_id: str, video_id: str) -> dict:
    """Extract a WebP poster frame from a video file."""
    settings = get_settings()
    ffmpeg = _resolve_binary(settings.ffmpeg_path, "ffmpeg")
    source = Path(source_path).resolve()
    _video_path, poster_path = _output_paths(product_id, video_id)
    command = [
        *_command_prefix(),
        ffmpeg,
        "-y",
        "-ss",
        VIDEO_POSTER_TIMESTAMP_SECONDS,
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        "scale='min(iw,-2)':min(1080,ih):force_original_aspect_ratio=decrease",
        "-c:v",
        "libwebp",
        "-quality",
        "82",
        str(poster_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=VIDEO_FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        poster_path.unlink(missing_ok=True)
        raise VideoProcessingError("poster extraction timed out") from exc
    if result.returncode != 0:
        poster_path.unlink(missing_ok=True)
        raise VideoProcessingError(f"poster extraction failed: {_stderr_tail(result)}")
    return {"poster_url": f"/static/products/{poster_path.name}"}


def unlink_video_files(*urls_or_paths: str | None) -> None:
    """Best-effort removal of video, poster, or temp files under approved roots."""
    settings = get_settings()
    static_root = Path(settings.static_file_path).resolve()
    temp_root = Path(settings.video_upload_temp_path).resolve()
    for item in urls_or_paths:
        if not item:
            continue
        if item.startswith("/static/"):
            path = (static_root / item.removeprefix("/static/").lstrip("/")).resolve()
            root = static_root
        else:
            path = Path(item).resolve()
            root = temp_root
        try:
            path.relative_to(root)
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("product_video_unlink_failed", path=str(path), error=str(exc))
        except ValueError:
            logger.warning("product_video_unlink_rejected", path=str(path))
