## Context

Products have a still-image gallery (`product_images`: up to 6 WebP images, one primary, `sort_order`, served from `/static/products/`, processed synchronously by `app/services/image_service.py` with Pillow). The owner wants one high-resolution video per product, ≤30s, displayed **inside** that gallery.

This document records the decisions reached during exploration. The dominant constraint is that **video transcoding cannot run in the request path** (ffmpeg on a 30s 1080p clip takes seconds-to-tens-of-seconds and pins a CPU core; Layer 1's budget is <200ms). The codebase already has a durable async-job precedent — the email outbox (`order_emails` + claim table + lease + background sweeper on a ~15s tick in `app/main.py`) — and this change mirrors that shape, simplified because we chose fail-fast.

## Goals / Non-Goals

**Goals:**
- One self-hosted video per product, ≤30s, up to 1080p, with sound.
- Transcode every upload to a normalized, browser-universal MP4 (guaranteed compatibility + consistent quality).
- Video displayed as a slide *within* the existing photo gallery, ordered by `sort_order`.
- Inline muted-autoplay loop; click to enlarge into a lightbox with sound + controls.
- The store (Layer 1) is never starved of CPU by transcoding, and never affected by a transcode failure.
- The existing `product_images` gallery is left completely untouched.

**Non-Goals:**
- Multiple videos per product; adaptive bitrate/HLS; automatic retry/backoff; multi-worker claim races; CDN/object storage; captions; custom player skin; video in CSV import; video on the product grid.

## Decisions

### 1. Self-host, don't embed

Rejected YouTube/Vimeo embeds. Rationale: iframe chrome (logo, suggested videos, "Watch Later") cheapens a luxury storefront and cannot sit cleanly inside a swipeable photo carousel. A 30s clip is small (~20–40MB at 1080p) and Oracle free tier gives ~10TB/month egress (~250k views) — bandwidth is not the constraint at this scale. The "video kills a VPS" concern is about long-form streaming, not a single short loop.

### 2. Separate `product_videos` table (one row per product), not unified `product_media`

Considered rebuilding `product_images` into a `product_media` table with a `media_type` discriminator. Rejected: per memory (`products-schema-migration-mechanism`), schema changes to this area require multiple order-synced edits (rebuild-via-`products_new`, FTS, legacy image seeding) and would rewrite the battle-tested reorder logic. Since the requirement is **exactly one video**, a dedicated single-row-per-product table:

- Enforces "exactly 1" for free (a `UNIQUE(product_id)` constraint).
- Leaves the image gallery 100% untouched (zero regression risk).
- Carries its own `sort_order` so the frontend interleaves the one video slide among the images at render time.

**Trade-off accepted:** "media" now has two code paths (images + video) and the gallery-ordering merge lives in the read/response layer. Acceptable for a single interleaved slide.

**Gallery merge rule (resolves the two-table `sort_order` ambiguity).** Images and the video carry independent `sort_order` values, so a naïve merge is ambiguous on ties. The video's `sort_order` is defined as an **insertion index into the image sequence**: the response layer sorts images by their `sort_order`, then inserts the video slide at position `video.sort_order` (0 = before the first image, `len(images)` or greater = after the last). On any collision the **video sorts before** the image at that index (deterministic tie-break). This keeps the image gallery's own ordering authoritative and gives the single video one unambiguous slot.

**File cleanup is explicit, not cascade.** FK enforcement is on (`PRAGMA foreign_keys=ON`), so `ON DELETE CASCADE` removes the `product_videos` **row** when a product is deleted — but it does **not** remove the `.mp4`/poster **files** under `/static`. Following the image pattern (`_unlink_image_files`), the video service SHALL explicitly unlink the output files (and any temp original) on: video delete, video replace, and product delete. Unlink is best-effort with a warning log on failure (mirrors `product_image_service._unlink_image_files`), never blocking the delete.

Proposed shape:

```sql
CREATE TABLE IF NOT EXISTS product_videos (
    id            TEXT PRIMARY KEY,                 -- uuid4 hex
    product_id    TEXT NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    status        TEXT NOT NULL,                    -- queued | transcoding | ready | failed
    source_path   TEXT,                             -- temp path to original; NULL once deleted
    video_url     TEXT,                             -- /static/products/<id>_video.mp4 (NULL until ready)
    poster_url    TEXT,                             -- /static/products/<id>_poster.webp
    duration_secs REAL,                             -- probed from source, ≤ 30
    sort_order    INTEGER NOT NULL DEFAULT 0,       -- position among gallery images
    failure_reason TEXT,                            -- human-readable, set when status='failed'
    lease_expires_at TEXT,                          -- orphan detection (see Decision 6)
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_product_videos_status ON product_videos(status);
```

### 3. Transcode every upload (async), fail-fast

Every upload is normalized — we do not serve arbitrary uploaded files. This guarantees browser compatibility and consistent quality regardless of what the owner's camera/editor produces.

**Fast path (upload request, Layer 1 <200ms):**
1. Validate container + size + probe duration with `ffprobe` (reject >30s here, instantly, before queuing).
2. Save the original to `video_upload_temp_path`.
3. Insert `product_videos` row with `status='queued'`.
4. Return `202 Accepted` with `status: "processing"`.

**Slow path (background sweeper tick, off the event loop):**
1. Claim a `queued` row (set `status='transcoding'`, set `lease_expires_at`).
2. Run ffmpeg → normalized MP4 (Decision 4).
3. Extract poster frame (Decision 5).
4. `status='ready'`, populate `video_url`/`poster_url`, delete the original, clear `source_path`.
5. On any error → `status='failed'`, set `failure_reason`; **no retry**.

State machine:

```
   queued ──▶ transcoding ──▶ ready
                   │
                   └──▶ failed (failure_reason)  →  owner sees why, re-uploads
```

**Why fail-fast (vs. the email outbox's retry/backoff):** the owner is a human uploading their own clip and watching the result; a clear "why it failed" message + re-upload is simpler and more honest than silent retries. This lets us **drop** the outbox's `attempts` counter, `next_attempt_at` backoff, and auto-redelivery. We keep only a lightweight lease for crash detection (Decision 6).

**Re-upload while a transcode is in flight.** Replacing a video is well-defined only for a `ready`/`failed` product. If a video is currently `queued` or `transcoding`, a new upload SHALL be **rejected with HTTP `409 Conflict`** (`video is still processing`) rather than racing the in-flight ffmpeg job and its partial output files. The owner retries after processing settles (or after it fails). This avoids orphaned output files and a second transcode claiming the same product concurrently.

### 4. Normalized MP4 target

- Container: MP4, `-movflags +faststart` (moov atom at front → progressive playback while downloading).
- Video: H.264 **High** profile, `-pix_fmt yuv420p` (Safari refuses other pixel formats), CRF ~20 (visually high quality), max height 1080p (downscale only, never upscale), preserve aspect ratio.
- **Audio: kept** — AAC ~128kbps. The video has sound the visitor is meant to hear (drives the lightbox playback in Decision 7). This is the key departure from a "silent moving-photo loop."
- Exact ffmpeg args and CRF live in `app/constants.py` as named constants.

### 5. Poster frame

With ffmpeg present, extract a real frame (default ~1s in) as the poster, saved as WebP to match the image pipeline. **Fallback:** if extraction fails or as a simpler default, reuse the product's primary image thumbnail. The poster is required — it is what the inline tile shows before/while the video buffers, and the fallback when autoplay is blocked (iOS Low Power Mode, `prefers-reduced-motion`). *(Open question in proposal: extracted-frame default vs. primary-image default.)*

### 6. Layer 1 CPU protection

Email sending is IO-bound (waits on the network); ffmpeg is **CPU-bound** and will eat every core on a small VPS, blowing the store's <200ms budget. Mitigations, all first-class requirements:

- **Concurrency = 1 (global)**: at most one transcode at a time across the whole deployment — **not** per-worker. Production runs **2 uvicorn workers** (the reason the email outbox uses a claim table), so both sweeper ticks can fire. The claim SHALL be a single atomic `UPDATE product_videos SET status='transcoding', lease_expires_at=? WHERE status='queued' AND NOT EXISTS (SELECT 1 FROM product_videos WHERE status='transcoding' AND lease_expires_at > now)` (or equivalent guarded update). SQLite's single-writer property makes the row transition atomic; the `NOT EXISTS` guard enforces the global limit of one live transcode. A worker whose claim update affects 0 rows does nothing this tick.
- **Off the event loop**: ffmpeg runs as a subprocess (via a thread / `asyncio` subprocess), never blocking request handling.
- **`nice` / `ionice`**: the ffmpeg process is de-prioritized for CPU and IO so Layer 1 requests always win.
- **Lease for orphan detection**: if the server crashes mid-transcode, on the next sweep a `transcoding` row past its `lease_expires_at` is marked `failed` with reason `"processing interrupted"` (no retry — owner re-uploads).

### 7. Playback behavior (frontend)

Browsers block autoplay **with** sound, so the two contexts differ:

```
IN GALLERY (inline tile, detail page only)     ON CLICK (lightbox)
──────────────────────────────────────────     ───────────────────
<video muted autoplay loop playsinline>         enlarge → modal overlay
moving-photo feel, no controls                  unmute, native controls
                                                full sound, scrub, ❚❚
```

- `playsinline` is **mandatory** — without it iOS Safari force-fullscreens the muted autoplay and breaks the effect.
- **Detail gallery only.** The product grid/cards show the poster still — no autoplay (12 auto-looping videos on a listing page is a bandwidth + jank disaster).
- **`prefers-reduced-motion`**: show the poster (with a play affordance), do not autoplay.
- Poster is the universal fallback when autoplay is blocked.

### 8. Failure reasons surfaced to the owner

Captured at the fast-validate step (ffprobe) or from ffmpeg stderr, mapped to human-readable strings stored in `failure_reason` and shown in admin:

| Reason | Detected |
|---|---|
| `duration 42s exceeds 30s limit` | ffprobe, pre-queue (instant `422`) |
| `resolution below minimum` / `unsupported source codec` | ffprobe, pre-queue |
| `file corrupted or unreadable` | ffprobe / ffmpeg |
| `processing interrupted` | orphaned lease (Decision 6) |
| `transcode failed: <ffmpeg stderr tail>` | ffmpeg non-zero exit |

Duration/format failures are caught synchronously in the upload request (fast `422`, nothing queued). Only genuine transcode failures reach the `failed` status.

### 9. Validation is harder than images — ffprobe is required

Images validate via magic bytes (JPEG/PNG). Video containers can't be trusted that cheaply. `ffprobe` is the source of truth for duration, codec, and dimensions at the fast-validate step. If `ffmpeg`/`ffprobe` are absent on the host, uploads are rejected with a clear ops-facing message and the store is otherwise unaffected (graceful degradation — no video features, everything else works).

## Risks / Trade-offs

- **New system dependency (ffmpeg/ffprobe).** Must be installed on the VPS and documented in deploy notes. Mitigation: runtime detection + clear rejection message; store unaffected if missing.
- **Two media code paths.** Images and video are managed separately; the gallery-ordering merge lives in the response layer. Accepted as the cost of not migrating the image gallery.
- **CPU spike during transcode.** Mitigated by concurrency=1 + nice/ionice + off-loop subprocess (Decision 6). Worst case: one transcode makes the store slightly less snappy for a few seconds; it never fails a request.
- **Disk growth.** One MP4 + one poster per product. Bounded and small at catalog scale.
- **Raw upload size.** Pre-transcode source from a phone can be 100–200MB for 30s. `max_video_upload_bytes` must be generous but bounded to protect temp disk (open question).

## Migration Notes

- Additive only: new `product_videos` table, new columns nowhere else except `ProductResponse.video` (response model, not DB). No change to `products` or `product_images` — avoids the `products_new` rebuild dance entirely.
- No data backfill (no existing videos).
- Deploy prerequisite: `ffmpeg`/`ffprobe` on the host.
