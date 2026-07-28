## 1. Schema & Config

- [x] 1.1 Add `product_videos` table (one row per product via `UNIQUE(product_id)`, `ON DELETE CASCADE`) + `idx_product_videos_status` index in `app/database.py`
- [x] 1.2 Add config to `app/config.py`: `ffmpeg_path`, `ffprobe_path`, `video_upload_temp_path`, `max_video_upload_bytes`, `max_video_duration_seconds` (30)
- [x] 1.3 Add transcode constants to `app/constants.py`: H.264/CRF/max-height/faststart args, AAC bitrate, poster timestamp, `nice`/`ionice` settings, sweeper tick interval, lease seconds

## 2. Backend — Video Service (ffmpeg/ffprobe)

- [x] 2.1 Create `app/services/video_service.py` — exceptions (mirror `image_service` style): `VideoServiceError`, `InvalidVideoTypeError`, `VideoTooLongError`, `FileTooLargeError`, `VideoProcessingError`, `FfmpegUnavailableError`
- [x] 2.2 `probe_video(source_path)` — ffprobe wrapper returning duration/codec/dimensions; raises on unreadable/unsupported
- [x] 2.3 `validate_video_upload(bytes/path, product_id)` — size cap, product-id slug check, path safety, duration ≤ 30 via probe → maps failures to human-readable reasons
- [x] 2.4 `transcode(source_path, product_id) -> {video_url, poster_url}` — ffmpeg to normalized MP4 (H.264 High, yuv420p, +faststart, ≤1080p, AAC), run as subprocess with `nice`/`ionice`, off the event loop; **ffmpeg/ffprobe invoked with an argument list, never `shell=True`** (command-injection guard); path-traversal prevention like `image_service`
- [x] 2.5 `extract_poster(source_or_output, product_id)` — ffmpeg frame → WebP; fallback to product primary image thumbnail
- [x] 2.6 Runtime detection: missing ffmpeg/ffprobe → `FfmpegUnavailableError` with operator-facing message
- [x] 2.7 `unlink_video_files(*urls)` — best-effort disk removal of MP4/poster/temp-original under the static root (mirror `product_image_service._unlink_image_files`: path-confined, warn-on-failure, non-fatal)

## 3. Backend — Gallery Orchestration & Pipeline

- [x] 3.1 Create `app/services/product_video_service.py` (mirrors `product_image_service.py`): intake upload → store original + insert `queued` row (`202`), get status, delete (unlink files via 2.7), set `sort_order`, `with_video_field(product, video_row)` for response assembly. **Reject upload with `409` when the product's video is `queued`/`transcoding`** (re-upload race). Replace of a `ready`/`failed` video unlinks the old output files.
- [x] 3.2 Implement sweeper `drain_video_transcodes()` — **atomic global claim** (`UPDATE … SET status='transcoding', lease_expires_at=? WHERE status='queued' AND NOT EXISTS(live transcoding)`) to enforce concurrency=1 across both prod workers; transcode, extract poster, mark `ready` + delete original; on error mark `failed` with reason; orphaned `transcoding` past lease → `failed('processing interrupted')`
- [x] 3.3 Wire the sweeper into `app/main.py` lifespan as a new tick (alongside the email-outbox drain), off the event loop
- [x] 3.4 Add `app/models/products.py`: `ProductVideo` model (video_url, poster_url, sort_order, duration_secs, status); add optional `video: ProductVideo | None` to `ProductResponse` (present only when `ready`)
- [x] 3.5 Gallery merge: assemble the public gallery by inserting the video slide at `sort_order` into the image sequence (0 = before first, ≥ count = last; collision → video first) — deterministic order, in the response layer

## 4. Backend — Admin Routes

- [x] 4.1 `POST /v1/admin/products/{id}/video` — upload (multipart), `require_admin`, validate + queue, returns `202` + status; replaces any existing video
- [x] 4.2 `GET /v1/admin/products/{id}/video` — status + failure_reason for admin view
- [x] 4.3 `DELETE /v1/admin/products/{id}/video` — remove row + output files (`204`)
- [x] 4.4 `PATCH /v1/admin/products/{id}/video` — set `sort_order` (gallery position)
- [x] 4.5 Map new exceptions in `app/exceptions.py`: too-long/oversized/unreadable → `422`, re-upload while processing → `409`, ffmpeg-unavailable → `503` (clear message)
- [x] 4.6 Hook product deletion (`product_service`/`admin_service` delete path) to unlink the product's video output files before/after the cascade removes the row (cascade drops the row only, not the disk files)

## 5. Backend — Tests

- [x] 5.1 `video_service`: probe happy path; duration > 30 → reason; corrupted → reason; oversized → reason; missing ffmpeg → graceful error (mock subprocess)
- [x] 5.2 Pipeline: queued → ready (mock ffmpeg success); ffmpeg non-zero → `failed` + reason, no retry; orphaned lease → `failed('processing interrupted')`
- [x] 5.3 Concurrency: two `queued`, one sweep → exactly one `transcoding`
- [x] 5.4 Public `ProductResponse`: `video` present only when `ready`; omitted for queued/transcoding/failed/none
- [x] 5.5 Admin routes: upload requires admin (401/403 for non-admin), replace keeps exactly one, delete removes files, sort_order updates
- [x] 5.6 Store-unaffected: with ffmpeg mocked to fail, product/cart/checkout routes still succeed
- [x] 5.7 Re-upload while `queued`/`transcoding` → `409`; replace of `ready` video unlinks old files
- [x] 5.8 Atomic claim: two concurrent sweeps over one `queued` row → exactly one wins (0 rows updated for the loser)
- [x] 5.9 Gallery merge order: video `sort_order` inserts at index; ≥ count → last; collision → video first (deterministic)
- [x] 5.10 Product delete unlinks video files AND removes the row

## 6. Frontend

- [x] 6.1 `lib/types.ts` — add `ProductVideo` interface + optional `video` on the product type
- [x] 6.2 `ProductGallery.tsx` — interleave the video slide by `sort_order`; inline `<video muted autoplay loop playsinline>` with poster; suppress autoplay on `prefers-reduced-motion` (show poster)
- [x] 6.3 New `VideoLightbox` component — click inline video → enlarge, unmute, native controls
- [x] 6.4 `ProductCard` — show poster still only, never autoplay in grid
- [x] 6.5 Admin product form — video upload panel: upload/replace/delete, processing status, failure reason, gallery-position control
- [x] 6.6 `lib/mock-api.ts` — return a sample `ready` video for one product
- [x] 6.7 Frontend tests: gallery renders video slide at position; grid shows poster only; reduced-motion path

## 7. Docs & Deploy

- [x] 7.1 Document `ffmpeg`/`ffprobe` install as a VPS deploy prerequisite; note graceful degradation if absent
- [x] 7.2 Note temp-dir + static-dir disk usage and `max_video_upload_bytes` in ops notes
- [x] 7.3 Update `CLAUDE.md` app structure with `video_service.py` / `product_video_service.py` and the new sweeper tick
- [x] 7.4 Raise nginx `client_max_body_size` on the video upload route (`deploy/`) to exceed `max_video_upload_bytes` — the default (~1MB) rejects raw uploads with `413` before FastAPI sees them
