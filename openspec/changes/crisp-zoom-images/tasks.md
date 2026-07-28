## 1. Backend — image processing (`app/services/image_service.py`)

- [x] 1.1 Raise `MAX_FILE_SIZE` from `5 * 1024 * 1024` to `25 * 1024 * 1024`; update the docstrings/messages in `validate_image_file` that say "5MB" to "25MB"
- [x] 1.2 Add zoom output constants: `_ZOOM_MAX_SIZE = (2400, 3000)` and `_ZOOM_QUALITY = 90`
- [x] 1.3 Bump main output: `_MAIN_MAX_SIZE = (2000, 2500)` and `_MAIN_QUALITY = 88`
- [x] 1.4 In `process_image`, build a `zoom_path` stem (`{filename_stem}_zoom.webp`) and include it in the path-traversal `relative_to(base_dir)` safety check alongside main/thumb
- [x] 1.5 Generate and save the zoom derivative from a fresh `img.copy()` using `thumbnail(_ZOOM_MAX_SIZE, LANCZOS)` and `save(..., format="WEBP", quality=_ZOOM_QUALITY)`
- [x] 1.6 Add `zoom_url` (`/static/products/{filename_stem}_zoom.webp`) to the returned dict
- [x] 1.7 Confirm `MAX_IMAGE_PIXELS` is left unchanged (25MP safety ceiling — verified, not modified)

## 2. Backend — upload route (`app/routes/admin.py`)

- [x] 2.1 Raise the streaming chunk-guard limit (the `if len(chunks) > MAX_FILE_SIZE` path, ~line 740) to the new 25MB `MAX_FILE_SIZE`; update the "exceeds maximum of 5MB" messages to "25MB"
- [x] 2.2 Ensure the persisted `product_images` row and the upload response include `zoom_url` from `process_image`'s result
- [x] 2.3 Verify `FileTooLargeError` still maps to 422 `file_too_large` with a message stating 25MB

## 3. Backend — schema (`app/database.py`)

- [x] 3.1 Add `zoom_url TEXT` to the `CREATE TABLE ... product_images` definition (both the `_SCHEMA_SQL` and any secondary `product_images` DDL block — the two locations near lines 34 and 331), positioned right after `thumbnail_url`
- [x] 3.2 Confirm NO rebuild/backfill work is added — project is not live, no data to migrate (no `products_new`-style copy, no `select_exprs`, no legacy backfill for zoom)
- [x] 3.3 Verify fresh DB init yields a `product_images` table with a `zoom_url` column

## 4. Backend — model (`app/models/products.py`)

- [x] 4.1 Add `zoom_url` to the `ProductImage` model (positioned after `thumbnail_url`; nullable for fallback compatibility)
- [x] 4.2 Confirm `zoom_url` flows through wherever image rows are serialized into `ProductResponse.images` / admin image responses

## 5. Frontend — types & mocks

- [x] 5.1 Add `zoom_url` to the `ProductImage` interface in `frontend/lib/types.ts` (nullable for fallback compatibility)
- [x] 5.2 Add `zoom_url` values to any image fixtures in `frontend/lib/mock-api.ts` so mock mode renders the lightbox

## 6. Frontend — retina hero + zoom lightbox (`frontend/components/products/`)

- [x] 6.1 Ensure the gallery hero renders the (now sharper) `image_url` main asset; verify `sizes` still reflects the ~50vw layout
- [x] 6.2 Add a click-to-zoom affordance on the hero (button/overlay with accessible label, e.g. "Zoom image")
- [x] 6.3 Create a lightbox component: dialog role, focus trap, Esc + backdrop-click to close, renders `selectedImage.zoom_url`
- [x] 6.4 Load the zoom asset lazily — only when the lightbox opens (no fetch on initial product page load)
- [x] 6.5 Fallback: if `zoom_url` is null/absent, the lightbox uses `image_url`
- [x] 6.6 Add i18n strings for zoom affordance / lightbox close to `frontend/messages/en.json` + `bg.json`

## 7. Frontend — admin upload soft-warning (`frontend/components/admin/`)

- [x] 7.1 On file select, read `file.size`; if `> 25MB` block with inline error "Maximum image size is 25 MB" and do not upload
- [x] 7.2 If `15MB ≤ size ≤ 25MB`, show a confirm dialog ("This image is large (N MB)…") with Cancel / Add anyway; only proceed on confirm
- [x] 7.3 If `< 15MB`, proceed with no prompt
- [x] 7.4 Add i18n strings for the warning + block messages to `en.json` + `bg.json`

## 8. Deploy

- [x] 8.1 Raise Nginx `client_max_body_size` to `27m` (documented in the `image-upload` spec; config not committed in-repo — note in deploy runbook)

## 9. Tests

- [x] 9.1 `image_service`: file exactly at 25MB accepted; >25MB raises `FileTooLargeError`
- [x] 9.2 `image_service`: `process_image` writes three files (thumb/main/zoom) with expected max dimensions and never upscales small inputs
- [x] 9.3 `image_service`: returned dict includes `image_url`, `thumbnail_url`, `zoom_url`
- [x] 9.4 Route: upload response and product API include `zoom_url`; `>25MB` → 422 `file_too_large`
- [x] 9.5 Schema: fresh DB `product_images` has a `zoom_url` column
- [x] 9.6 Frontend: file <15MB uploads silently; 15–25MB triggers confirm (cancel aborts, confirm proceeds); >25MB blocked
- [x] 9.7 Frontend: lightbox opens on hero click, renders `zoom_url`, closes on Esc/backdrop, and falls back to `image_url` when `zoom_url` is null
