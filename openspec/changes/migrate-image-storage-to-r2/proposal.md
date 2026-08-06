## Why

Product image and video media currently lives on the single Oracle Cloud VPS's local disk (`STATIC_FILE_PATH/products/`) and is served through the FastAPI `/static` mount, which Nginx proxies straight through to the app. This couples durable media to one ephemeral, size-limited server, makes every media request compete with the checkout path for app resources, and blocks any move to multiple app instances (each would have its own disjoint disk). Moving media to Cloudflare R2 — an S3-compatible object store with zero egress fees and a global CDN — decouples storage from the app server, removes media serving from the critical path, and gives us durable, horizontally-scalable storage.

## What Changes

- **Add an R2-backed object storage layer** for all product image and video media (main/thumbnail/zoom WebP images, transcoded MP4 video, WebP poster). Uploads and transcoder output are written directly to a single R2 bucket instead of local disk.
- **DB stores full public R2 URLs** (e.g. `https://media.example.com/products/...`) in `product_images.image_url/thumbnail_url/zoom_url` and `product_videos.video_url/poster_url`, replacing the relative `/static/products/...` scheme for new writes. The frontend `resolveMediaUrl` already passes absolute URLs through unchanged.
- **BREAKING (deployment):** The `/static` `StaticFiles` mount is retired for product media, and Nginx no longer proxies `/static/`. Media is served publicly from R2 via a custom domain / `r2.dev` URL. Requires a completed backfill before cutover.
- **One-time backfill script** uploads every existing on-disk media file to R2 and rewrites the corresponding DB URL columns to R2 URLs (idempotent, resumable, dry-run supported).
- **Media deletion targets R2:** image/video delete paths issue R2 `DeleteObject` calls in place of local `unlink`. The soft-delete image-orphan gap (deactivated products leave image objects) is addressed as part of cleanup accounting.
- **Add an S3-compatible client dependency** (`boto3`) and R2 configuration settings (bucket, endpoint, access keys, public base URL) to `app/config.py`.
- **Raw video uploads still stage locally** in `video_upload_temp_path` before ffmpeg transcode; only the transcoded outputs move to R2. `product_videos.source_path` remains a local temp path until the video is ready.
- **Frontend `next.config.js`** gains `images.remotePatterns` for the R2 media domain so `next/image` can be enabled later; `NEXT_PUBLIC_MEDIA_URL` points at the R2 domain.

## Capabilities

### New Capabilities
- `object-media-storage`: An S3-compatible object storage abstraction (R2 backend) that owns writing, deleting, and public-URL generation for product media objects, isolated behind a single service module. Includes configuration, credential handling, error wrapping, and a one-time disk→R2 backfill.

### Modified Capabilities
- `image-upload`: Image write path stores WebP variants in R2 and records full R2 public URLs (was: writes to `{static_file_path}/products` and records `/static/products/...` relative URLs). File validation, resize/variant, and cap behavior are unchanged.
- `product-image-gallery`: Gallery add/delete operate against R2 (delete issues `DeleteObject`; `image_url/thumbnail_url/zoom_url` hold R2 URLs). CSV-import of external URLs is unchanged (already stores absolute URLs).
- `product-video`: Transcoder writes MP4 + poster to R2 and records R2 public URLs; video delete removes R2 objects. Raw-upload staging, transcode queue/status machine, and duration/size limits are unchanged.

## Impact

- **Backend code:** `app/services/image_service.py`, `app/services/product_image_service.py`, `app/services/video_service.py`, `app/services/product_video_service.py`, `app/services/about_service.py` (reuses image write path); new `app/services/object_storage_service.py`; `app/main.py` (`/static` mount removal, dir-creation startup); `app/config.py` (R2 settings).
- **APIs:** No change to route contracts (`POST/DELETE .../images`, `.../video`); response shapes unchanged (still `image_url`, `thumbnail_url`, etc. — values become absolute R2 URLs).
- **Database:** No schema change. `product_images` and `product_videos` URL columns hold R2 URLs going forward; backfill rewrites existing rows. `source_path` (raw temp path) unchanged.
- **Dependencies:** Add `boto3` (S3-compatible client). Pillow/ffmpeg/ffprobe unchanged.
- **Frontend:** `frontend/next.config.js` (`remotePatterns`), env `NEXT_PUBLIC_MEDIA_URL`. `resolveMediaUrl` needs no change.
- **Infra/deploy:** Nginx config drops the `/static/` proxy for media; new R2 bucket + credentials + public domain; `compose.yml`/`.env` gain R2 vars, static volume can be retired post-cutover.
- **Tests:** `tests/test_image.py`, `tests/test_product_image_service.py`, `tests/test_video_service.py`, `tests/test_product_video_service.py`, `tests/test_admin_routes.py`, `tests/realapp/test_about_routes.py` — media assertions move from disk checks to storage-layer calls (object storage mocked/faked in tests).
