## Context

All product image and video media currently lives on the single Oracle Cloud VPS's local disk under `STATIC_FILE_PATH/products/` (default `./static/products`, `/data/static/products` in Docker) and is served by FastAPI's `StaticFiles` mount at `/static` (`app/main.py:511–515`), which Nginx `proxy_pass`es straight to the app rather than serving via a filesystem alias. The DB stores relative `/static/products/...` URLs in `product_images.image_url/thumbnail_url/zoom_url` and `product_videos.video_url/poster_url`. There is no S3/R2/boto3 client in the dependency tree today.

Media write happens in two services: `image_service.process_image` (writes three WebP variants) and the video transcode pipeline (`video_service.transcode` + `extract_poster`, driven by `product_video_service.drain_video_transcodes`). URL strings are hardcoded as `/static/products/...` in `image_service.py`, `video_service.py`, `product_video_service.py`, and `product_image_service._derive_thumbnail_url`. `about_service.py` reuses `image_service.process_image` for owner images. Cleanup lives in `product_image_service._unlink_image_files` and `video_service.unlink_video_files`. The frontend's `resolveMediaUrl` (`frontend/lib/media.ts`) already passes absolute `http(s)` URLs through unchanged and only prefixes `NEXT_PUBLIC_MEDIA_URL` for `/static/...` paths.

**Confirmed decisions (from proposal Q&A):** R2 fully replaces disk for product media; a one-time backfill migrates existing files; objects are served from a public R2 bucket via a custom domain / `r2.dev` URL (full public URLs stored in the DB).

**Constraints:** Layer-boundary rule — media storage must stay isolated from the critical checkout path; the R2 client is imported only in the new storage service. Tests must not require a live R2 bucket. Raw video uploads must still stage locally for ffmpeg (R2 is not a POSIX filesystem ffmpeg can read/write directly).

## Goals / Non-Goals

**Goals:**
- Write all new product image/video media to a single R2 bucket and store full public R2 URLs in the DB.
- Isolate all S3 API usage behind one service module (`object_storage_service.py`); the `boto3` import lives only there.
- Retire the `/static` product-media mount and the Nginx `/static/` proxy after cutover; serve media directly from R2's public domain.
- Provide an idempotent, resumable, dry-run-capable backfill script for existing on-disk media.
- Keep route contracts and response shapes unchanged (URL values become absolute R2 URLs).
- Keep media storage failures out of the critical path (checkout unaffected by R2 outage).
- Close the pre-existing orphan gap: deactivating a product now removes its image objects too.

**Non-Goals:**
- Presigned/private-object access or a backend media proxy (public bucket chosen).
- Enabling `next/image` optimization now (we only add `remotePatterns` so it *can* be enabled later; `images.unoptimized: true` stays).
- Changing image/video processing behavior (sizes, quality, EXIF handling, transcode args, duration/size limits) — all unchanged.
- Moving raw video upload staging off local disk.
- Any DB schema change (columns and types are unchanged; only values change).
- Multi-region/multi-bucket strategy; a single bucket + public base URL is sufficient.

## Decisions

### Decision 1: Single object-storage service wrapping boto3 against R2
Add `app/services/object_storage_service.py` exposing a small API: `upload_bytes(key, data, content_type) -> public_url`, `delete_object(key)`, `public_url(key)`, and `object_key_for(...)` helpers. It builds a `boto3` S3 client with `endpoint_url=r2_endpoint_url`, `region_name="auto"`, S3v4 signing, from config. S3 client construction is lazy/module-cached so importing the module has no side effects at test collection.

**Why:** Concentrates the only new dependency and the only S3 API surface in one file, satisfying the layer-isolation rule and making it trivially mockable in tests. **Alternatives considered:** (a) `aioboto3` for async — rejected: uploads already run in a threadpool (`asyncio.to_thread` / route threadpool), boto3 sync is simpler and the transcode loop is background; (b) raw `httpx` signing R2 requests by hand — rejected: reimplementing SigV4 is error-prone; (c) spreading S3 calls across the existing services — rejected: violates isolation and multiplies the mock surface.

### Decision 2: Store full public R2 URLs in the DB; no schema change
Media URL columns keep their types and simply hold absolute `https://{public-base}/products/...` URLs going forward. Object keys reuse the current filename stems under a `products/` prefix.

**Why:** The frontend already passes absolute URLs through `resolveMediaUrl` untouched, so storing full URLs needs zero frontend URL-rewrite logic and no schema migration. Reusing stems keeps keys predictable and makes the backfill a mechanical `/static/products/X` → `products/X` mapping. **Alternatives considered:** storing bare object keys and composing the URL at read time — rejected: would require touching every read path and the frontend, and would diverge from how CSV-imported absolute URLs are already stored.

### Decision 3: Upload-before-DB-write ordering; wrapped errors
The write path uploads all variants to R2 first, then inserts/updates the DB row with the returned public URLs. Any botocore error is caught in the service and re-raised as a domain exception (e.g. `MediaStorageError`) so routes translate it to a clean 5xx/502 envelope, never leaking botocore.

**Why:** Guarantees the DB never references an object that failed to upload (no broken image rows). Mirrors the existing "process then insert" flow. **Trade-off:** a DB failure *after* a successful upload can orphan an object in R2 — acceptable and rare; the backfill/cleanup accounting and eventual object-lifecycle rules can sweep these; matches today's disk behavior where a post-write crash also orphans files.

### Decision 4: Delete issues best-effort R2 DeleteObject
`_unlink_image_files` and `unlink_video_files` are reworked to call `object_storage_service.delete_object(key)` (derived from the stored URL) instead of `Path.unlink`. Failures are logged, not fatal — same contract as today. A stored URL that isn't under our public base (e.g. legacy `/static/...` pre-cutover, or an external CSV URL) is handled: `/static/...` still unlinks from disk during the transition; external URLs are skipped.

**Why:** Preserves the current best-effort cleanup semantics and keeps delete resilient during the migration window when both URL shapes may coexist.

### Decision 5: Video — transcode locally, upload outputs to R2
Raw uploads keep staging in `video_upload_temp_path`; ffmpeg reads/writes local temp files as today. After a successful transcode + poster extraction, the pipeline uploads the MP4 and poster to R2, sets `video_url`/`poster_url` to R2 public URLs, nulls `source_path`, and unlinks the local temp outputs. On upload failure the row does not go `ready` and the existing fail/cleanup path runs.

**Why:** ffmpeg needs a real filesystem; R2 is object storage. Only the durable outputs belong in R2. The poster-fallback-to-primary-thumbnail path keeps working because that thumbnail is itself an R2 URL post-migration.

### Decision 6: One-time backfill as a script under `scripts/`
`scripts/backfill_media_to_r2.py`: iterate `product_images` and `product_videos` rows, for each `/static/products/...` URL resolve the on-disk file, upload under the derived key, and rewrite the column to the R2 public URL. Idempotent (skip rows already pointing at the public base), resumable (per-row commit), `--dry-run` flag, and a run summary (uploaded / skipped / missing-file counts). External absolute URLs left untouched.

**Why:** A script (not a startup migration) keeps a potentially long, network-bound, one-time operation out of app boot and lets us dry-run and re-run safely. **Alternatives considered:** Alembic data migration — rejected: uploading many files inside a migration is slow, hard to resume, and couples deploy timing to upload throughput.

### Decision 7: Retire `/static` product-media mount + Nginx proxy at cutover
After backfill completes and is verified, remove the product-media reliance on the `/static` `StaticFiles` mount and drop the Nginx `/static/` proxy for media. The static Docker volume can be retired. `NEXT_PUBLIC_MEDIA_URL` points at the R2 public domain; `next.config.js` gains `images.remotePatterns` for it.

**Why:** Removing the app from the media serving path is the core benefit of the migration. Sequencing it *after* verified backfill avoids serving 404s. **Trade-off:** brief coordination needed at cutover (see Migration Plan).

### Decision 8: Tests use a fake object storage backend
Introduce a seam so tests inject a fake storage (in-memory dict of key→bytes) instead of hitting R2: either a module-level `set_backend()`/dependency or monkeypatching `object_storage_service`'s client. Media tests assert on storage calls / recorded keys+URLs rather than on-disk files.

**Why:** Keeps the parallel pytest suite hermetic and fast, with no network or credentials. **Alternatives considered:** `moto` (S3 mock library) — viable, but a tiny in-repo fake is lighter and avoids a new test dependency; we may still use `moto` for the client-construction/signing test if useful.

### Decision 9: Config additions
Add to `app/config.py`: `r2_bucket: str`, `r2_endpoint_url: str`, `r2_access_key_id: str`, `r2_secret_access_key: str`, `r2_public_base_url: str` (all sourced from env `R2_*`). Defaults are empty strings; media write paths raise a clear config error if unset when invoked (so dev/tests without R2 still boot). `boto3` added to `pyproject.toml`.

**Why:** Follows the pydantic-settings convention (no `os.getenv` in app code). Empty defaults keep the app bootable without R2 configured (only uploads fail), preserving the isolation guarantee.

## Risks / Trade-offs

- **Backfill uploads a large volume of files / partial completion** → Idempotent + resumable + per-row commit + dry-run; run summary reports missing files; can be re-run until clean before cutover.
- **Cutover serves 404s if `/static` is removed before backfill verified** → Strict ordering: backfill → verify sample of R2 URLs resolve → flip `NEXT_PUBLIC_MEDIA_URL` and remove mount/proxy. Rollback = re-point `NEXT_PUBLIC_MEDIA_URL` back to `/static` and restore the mount (files still on disk until volume retired).
- **DB write fails after successful R2 upload → orphaned object** → Accepted (rare, matches current disk behavior); optionally add an R2 lifecycle rule or a periodic orphan sweep later.
- **R2 outage during upload** → Uploads fail with a wrapped storage error; checkout and all Layer-1 flows are unaffected (storage service not on critical path). Retries left to the admin/transcode retry paths.
- **Public bucket exposes objects by key guessing** → Keys are non-secret product media meant to be public anyway; slug + uuid hex stems are unguessable enough and match today's public `/static` exposure. The public-bucket posture is deliberately **inherited from the current `/static` serving model, not newly introduced** by this change. Each object key is effectively a capability URL: the `product_id` slug is enumerable (it's in the sitemap) but the `uuid4().hex` component is 122 bits of randomness, so the full key is unguessable. Note there is no draft/embargo concept today — `is_active` is a soft-delete flag, and images can be uploaded to a not-yet-linked product, so any uploaded object (the `zoom` derivative being the highest-fidelity one) is publicly fetchable by URL the moment it is written, exactly as with `/static` today. This is accepted **only because all product media is intended to be public**. **Decision: keep it dead simple** — one public bucket, one upload path, no `visibility` flag, no signed/short-lived URLs. If a real draft/embargo-product feature is ever introduced, private/short-lived media (and likely on-the-fly image transforms that would retire the pre-baked `zoom` object) will be handled together in a dedicated future change; we are explicitly NOT planting a `visibility` seam now to avoid speculative generality on a mechanical migration.
- **Legacy vs R2 URL shapes coexist during migration** → Delete/cleanup handles both (`/static/...` unlink vs R2 delete vs external skip); `resolveMediaUrl` already handles both.
- **`about_service` owner images share the image write path** → Covered automatically since they call `image_service.process_image`; include an about-image assertion in tests.
- **New `boto3` dependency size/security** → Single well-maintained dependency, imported only in the storage service; acceptable.

## Migration Plan

1. Add `boto3` dep and R2 config settings; create `object_storage_service.py` with the fake-backend test seam.
2. Refactor `image_service`, `product_image_service`, `video_service`, `product_video_service` (and verify `about_service`) to upload to R2 and store R2 public URLs; rework delete paths to R2 `DeleteObject`; add image-object cleanup to product deactivation.
3. Update tests to use the fake backend; assert on keys/URLs.
4. Provision R2 bucket + credentials + public domain; set `R2_*` env and `NEXT_PUBLIC_MEDIA_URL`; add `next.config.js` `remotePatterns`.
5. Run `scripts/backfill_media_to_r2.py --dry-run`, review summary, then run for real until re-run is clean.
6. **Cutover:** verify a sample of DB R2 URLs resolve publicly → deploy backend without the `/static` product-media mount → drop Nginx `/static/` media proxy → point `NEXT_PUBLIC_MEDIA_URL` at R2.
7. Post-cutover: retire the `atelier_static` Docker volume once no `/static/...` URLs remain in the DB.

**Rollback:** Before volume retirement, on-disk files still exist. Restore the `/static` mount + Nginx proxy and re-point `NEXT_PUBLIC_MEDIA_URL` back to `/static`; DB rows rewritten to R2 URLs would need a reverse-map (keep the backfill's rewrite log to reverse). Simplest safe rollback window is between step 6 deploy and volume retirement.

## Open Questions

- **Custom domain vs `r2.dev`:** which public base URL for production (`media.<domain>` custom domain vs the bucket's `r2.dev` subdomain)? Affects `r2_public_base_url` and `next.config.js remotePatterns`. Assumed a custom domain; confirm at provisioning.
- **Content-addressing / cache headers:** do we want to set `Cache-Control`/immutable headers on upload (stems already include uuid, so objects are effectively immutable)? Recommended but not required for correctness.
- **Orphan sweep:** ship a periodic R2 orphan-cleanup now, or rely on upload-before-write + deactivation cleanup and defer? Leaning defer.
- **Private/embargo media + on-the-fly transforms:** RESOLVED — deferred. Keep this change dead simple (public bucket, pre-baked derivatives). Draft/embargo products, private/short-lived URLs, and edge image resizing (which would retire the pre-baked `zoom` object) are one coherent future change, to be opened only if a draft-product stage is actually planned.
