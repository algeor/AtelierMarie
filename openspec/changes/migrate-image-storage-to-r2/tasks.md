# Migrate image storage to R2 — Implementation Tasks

## 1. Dependencies & configuration

- [ ] 1.1 Add `boto3` to `pyproject.toml` dependencies and refresh the lockfile (`uv.lock`)
- [ ] 1.2 Add R2 settings to `app/config.py`: `r2_bucket`, `r2_endpoint_url`, `r2_access_key_id`, `r2_secret_access_key`, `r2_public_base_url` (env `R2_*`, empty-string defaults)
- [ ] 1.3 Add `R2_*` vars to `.env.example` and `.env.docker.example`; wire them into `compose.yml` backend env
- [ ] 1.4 Point `NEXT_PUBLIC_MEDIA_URL` (env/compose) at the R2 public domain and add `images.remotePatterns` for it in `frontend/next.config.js` (keep `images.unoptimized: true`)

## 2. Object storage service (new capability)

- [ ] 2.1 Create `app/services/object_storage_service.py` with a lazily-constructed, module-cached boto3 S3 client (`endpoint_url`, `region_name="auto"`, S3v4) built from config; `boto3` imported ONLY here
- [ ] 2.2 Implement `upload_bytes(key, data, content_type) -> public_url`, `delete_object(key)` (idempotent — missing object = success), and `public_url(key)` (normalize base trailing slash)
- [ ] 2.3 Implement `object_key_for(...)` helpers that reuse existing stems under `products/` and validate `product_id` against the slug allowlist (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`) / keep keys under the `products/` prefix
- [ ] 2.4 Add a `MediaStorageError` domain exception and wrap botocore errors; add a global handler entry / route translation so botocore internals never leak
- [ ] 2.5 Raise a clear config error from the write path when `R2_*` settings are unset (app still boots without R2)
- [ ] 2.6 Add a test seam: fake in-memory backend (key→bytes) injectable via `set_backend()`/dependency or monkeypatch

## 3. Image write & cleanup paths

- [ ] 3.1 Refactor `app/services/image_service.py` to upload the three WebP variants (main/thumb/zoom) to R2 with `ContentType: image/webp` and return R2 public URLs; remove `/static/products/...` string construction and local disk writes
- [ ] 3.2 Ensure upload-before-DB-write ordering in `app/services/product_image_service.py add_image` (no `product_images` row if upload failed)
- [ ] 3.3 Rework `product_image_service._unlink_image_files` (and `_derive_thumbnail_url`) to delete R2 objects by key (best-effort); handle legacy `/static/...` (disk unlink) and external absolute URLs (skip) during the transition
- [ ] 3.4 Verify `app/services/about_service.py` owner-image path works through the refactored `image_service` (R2 URLs) with no separate disk logic

## 4. Video write & cleanup paths

- [ ] 4.1 Update the transcode pipeline (`app/services/video_service.py` + `product_video_service.py drain_video_transcodes`) to upload the transcoded MP4 (`video/mp4`) and poster (`image/webp`) to R2 after successful transcode, set R2 public URLs, null `source_path`, and unlink local temp outputs
- [ ] 4.2 On R2 upload failure, do not transition to `ready`; route through the existing fail/cleanup path; keep raw uploads staged in `video_upload_temp_path`
- [ ] 4.3 Rework `video_service.unlink_video_files` to delete R2 objects for MP4/poster (best-effort) and still unlink local temp originals; confirm poster-fallback-to-primary-thumbnail still works with R2 URLs

## 5. Product deactivation orphan fix

- [ ] 5.1 In `product_service.deactivate_product`, delete the product's image objects from R2 (best-effort, logged) alongside the existing `delete_video_if_exists` call, closing the image-orphan gap

## 6. Retire the /static product-media mount

- [ ] 6.1 Remove the `/static` `StaticFiles` product-media mount and the products/static dir-creation on startup in `app/main.py` (keep `video_upload_temp_path` creation)
- [ ] 6.2 Drop the Nginx `/static/` media proxy in the deploy config; note retirement of the `atelier_static` Docker volume post-cutover

## 7. Backfill script

- [ ] 7.1 Create `scripts/backfill_media_to_r2.py` that iterates `product_images` and `product_videos`, uploads each `/static/products/...` file under its derived R2 key, and rewrites the DB column to the R2 public URL
- [ ] 7.2 Make it idempotent (skip rows already on the public base), resumable (per-row commit), and leave external absolute URLs untouched
- [ ] 7.3 Add `--dry-run` and a run summary (uploaded / skipped / missing-file counts); log-and-continue on missing source files; keep a rewrite log to support reverse-mapping on rollback

## 8. Tests

- [ ] 8.1 Wire the fake object storage backend into test fixtures (`tests/conftest.py` / `tests/realapp/conftest.py`)
- [ ] 8.2 Update `tests/test_image.py` and `tests/test_product_image_service.py` to assert on R2 keys/URLs and delete calls instead of on-disk files
- [ ] 8.3 Update `tests/test_video_service.py` and `tests/test_product_video_service.py` for R2 upload/delete of MP4+poster and local temp staging
- [ ] 8.4 Update `tests/test_admin_routes.py` image/video upload+delete endpoint tests for R2 URLs in responses
- [ ] 8.5 Update `tests/realapp/test_about_routes.py` for about-image R2 URLs
- [ ] 8.6 Add tests for `object_storage_service` (key derivation + slug allowlist, public-URL join, wrapped botocore error, idempotent delete)
- [ ] 8.7 Add a test that deactivating a product deletes its image objects; add a Layer-1-isolation test that checkout works while the storage backend raises
- [ ] 8.8 Add backfill tests: dry-run makes no changes, idempotent re-run skips migrated rows, missing file reported not fatal, external URLs untouched

## 9. Verification & cutover

- [ ] 9.1 Run `make lint` and `make test` (backend) + `make test-frontend`; confirm green
- [ ] 9.2 Provision R2 bucket + credentials + public domain; set `R2_*` and `NEXT_PUBLIC_MEDIA_URL` in the environment
- [ ] 9.3 Run the backfill `--dry-run`, review the summary, then run for real until a re-run is clean
- [ ] 9.4 Cutover: verify a sample of DB R2 URLs resolve publicly → deploy backend without the `/static` mount → drop the Nginx proxy → confirm storefront renders images/video from R2
- [ ] 9.5 Post-cutover: confirm no `/static/...` URLs remain in the DB, then retire the `atelier_static` Docker volume
