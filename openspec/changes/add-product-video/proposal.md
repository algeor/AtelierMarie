## Why

Product pages today show a still-image gallery (up to 6 WebP images, one primary, `sort_order`). For a luxury candle brand, a short moving shot — the flame flickering, wax pouring, the texture of the finish — sells the product in a way stills can't. The owner wants **one video per product, up to 30 seconds, in high resolution, displayed inside the existing photo gallery**.

Embedding YouTube/Vimeo was rejected: iframe chrome (logos, suggested videos) cheapens a premium storefront and can't sit cleanly inside a swipeable photo carousel. Self-hosting a short clip is viable — a well-encoded 1080p 30s MP4 is ~20–40MB, and the Oracle free tier provides ~10TB/month egress (~250k video views), so bandwidth is not the constraint at family-business scale.

The real cost is processing: unlike images (Pillow, synchronous, ~50ms), transcoding video with ffmpeg takes seconds-to-tens-of-seconds and pins a CPU core. That work **cannot** run in the upload request without blowing the Layer 1 <200ms budget and starving the store. This change therefore introduces an **asynchronous transcode pipeline** modeled on the existing durable email-outbox sweeper.

## What Changes

- New `product_videos` table — **exactly one row per product** (separate from `product_images`, which is left completely untouched). Columns for source/output URLs, poster URL, `sort_order` (to slot the video into the gallery among the images), duration, status, and a failure reason.
- New `app/services/video_service.py` — ffprobe validation, ffmpeg transcode invocation, poster extraction, path-safety (mirrors `image_service.py` structure).
- New `app/services/product_video_service.py` — gallery orchestration for the single video: upload intake, status, delete, and the response fields product readers expose (mirrors `product_image_service.py`).
- **Asynchronous transcode pipeline** (fail-fast, no retry): upload request validates + stores the original + inserts a `queued` row + returns `202`; a background sweeper (new tick in `app/main.py` lifespan) claims the job, transcodes, extracts a poster, marks `ready`, and deletes the original. On any failure → `failed` with a **detailed human-readable reason** for the owner; **no automatic retry** — the owner re-uploads.
- **Transcode target:** H.264 (High profile), `yuv420p`, `+faststart`, CRF ~20, capped at 1080p; **AAC audio kept** (the video has sound the visitor is meant to hear). Output is a normalized `.mp4`.
- **Layer 1 CPU protection:** at most **one** transcode at a time, run off the event loop via a subprocess with `nice`/`ionice` so store requests always win the CPU.
- **Playback (frontend, detail gallery only):** the video slide **autoplays muted + loops inline** (`playsinline`) as a moving-photo tile; **on click it enlarges into a lightbox and plays unmuted with controls**. Product grid/cards show the poster still only — no autoplay. Respects `prefers-reduced-motion` (poster instead of autoplay). Poster still is the graceful fallback when autoplay is blocked (iOS Low Power Mode).
- New public API surface: `ProductResponse` gains an optional `video` object (URL, poster URL, `sort_order`, duration) — present only when a video exists and is `ready`.
- New admin surface: upload video, view processing status / failure reason, replace, delete; set the video's position in the gallery ordering.
- New config: `ffmpeg_path`, `ffprobe_path`, `video_upload_temp_path`, `max_video_upload_bytes`, `max_video_duration_seconds` (30), transcode tuning constants in `app/constants.py`.

## Non-Goals

- More than one video per product.
- Adaptive bitrate / HLS / multiple renditions (single normalized MP4 only).
- Automatic transcode retry, job backoff, or a multi-worker claim race (single VPS, fail-fast).
- Video on the product grid/listing (poster still only there).
- Captions/subtitles, chapters, or a custom video player skin (native `<video>` controls in the lightbox).
- CDN or object storage — files live on local disk under `/static/products/`, same as images.
- Video in CSV bulk import.

## Capabilities

### New Capabilities
- `product-video`: Self-hosted single product video — async ffmpeg transcode pipeline (fail-fast), inline muted-autoplay gallery slide, click-to-enlarge lightbox with sound, poster frame, Layer 1 CPU protection.

### Modified Capabilities
- `product-catalog`: Public `ProductResponse` gains an optional `video` object, present only when a `ready` video exists.
- `admin-products`: Admin product management gains video upload, status/failure display, replace, delete, and gallery-position control.

## Related Changes

- **`crisp-zoom-images`** (concurrent, complementary — sharper/zoomable product *images*). The two changes touch the same surfaces; coordinate to avoid rework:
  - **Nginx `client_max_body_size`** — `crisp-zoom-images` raises it to `25m` for image uploads; video raw uploads need much more (~100–200MB). The video route's limit must **exceed** the image one. Prefer a **per-location** limit (a large cap only on the video upload endpoint) rather than a single global bump, so ordinary image uploads stay bounded.
  - **Gallery component** — both modify `ProductGallery.tsx` (this change interleaves the video slide; `crisp-zoom-images` sharpens the hero + adds an image zoom lightbox). Whichever lands second must merge, not overwrite.
  - **Lightbox reuse** — `crisp-zoom-images` builds an image zoom lightbox (dialog role, focus trap, Esc/backdrop close); this change's `VideoLightbox` should **share that component/interaction pattern** rather than duplicate it.
  - **Fresh-DB schema** — both edit the schema definition in `app/database.py` with "no migration, not live yet" (image `zoom_url` column vs. the new `product_videos` table). Independent tables, but the same file.
  - **mock-api fixtures** — both add media to `frontend/lib/mock-api.ts`; keep one product's fixture carrying both a `zoom_url` image set and a `ready` video.
  - **`/static` range support** — both rely on Starlette `StaticFiles` honoring HTTP Range (video seeking especially); no custom handler needed for either.

## Impact

- **Backend:** New `app/services/video_service.py`, `app/services/product_video_service.py`; new `product_videos` table + indexes in `app/database.py`; new admin routes for video upload/status/delete; a new sweeper tick in the `app/main.py` lifespan (alongside the email-outbox drain); `ProductResponse` gains `video`; new config + constants.
- **Frontend:** `ProductGallery.tsx` interleaves the video slide by `sort_order` (autoplay-muted-loop + click-to-lightbox); new `VideoLightbox` component; `ProductCard` shows poster only; admin product form gains a video upload/status/replace panel; `lib/types.ts` gains the `video` shape; mock-api returns a sample video.
- **System dependency:** `ffmpeg` + `ffprobe` binaries must be installed on the VPS (documented in deploy notes). Absent binaries → video features degrade gracefully (upload rejected with a clear message; store unaffected).
- **Layer boundary:** Entirely Layer 1 (product media is core e-commerce). The async sweeper is Layer 1 background work like the email outbox — it is **not** the analytics/ML Layer 2. No Layer 2 imports.
- **Storage/ops:** Transcoded MP4s + posters under `static/products/`; originals held in a temp dir only during processing, deleted on success. Disk growth ≈ one MP4 per product.

## Open Questions (Draft)

- Poster source default: extracted frame (e.g. at 1s) vs. reuse the product's primary image thumbnail. Leaning extracted frame with primary-image fallback — confirm in design.
- Minimum acceptable input resolution/bitrate to reject as "too low to look premium," or accept anything and let CRF do its job?
- Where the video sits by default in a fresh gallery — first slide, last, or owner sets it explicitly on upload?
- Exact `max_video_upload_bytes` ceiling for the *raw* upload (pre-transcode source can be large; 30s at phone-camera bitrates can be 100–200MB). Cap generously but bounded.
- Behavior when ffmpeg/ffprobe are missing at runtime — reject upload with a clear ops message (assumed) vs. a startup healthcheck warning.
