# Product Media Editor & Unified Lightbox Test Plan

## Automated Checks

Run these before release:

```bash
make lint
make test-backend
make test-frontend
cd frontend && npm run build
```

Expected result:
- Backend tests pass, including the image service EXIF orientation and quality/dimension cases.
- Frontend tests pass, including the ProductForm editor and ProductGallery lightbox specs.
- Next.js production build passes type checking.

## Backend — EXIF Orientation

Use the image service (`app/services/image_service.py`) directly or via `POST /v1/admin/products/{id}/images`.

1. Upload a photo carrying an EXIF orientation flag (e.g. a sideways phone photo, Orientation 6/8).
   - The saved main and zoom derivatives are upright — pixel dimensions match the visually-upright result, not the raw sensor orientation.
   - No EXIF metadata is written to the WebP output; orientation is baked into the pixels.

2. Upload an editor-produced blob (already cropped/rotated in the admin editor).
   - `exif_transpose` is a no-op (editor blobs carry no EXIF); the image is saved as framed, not double-rotated.

## Backend — Quality & Dimensions

1. Upload a known **landscape** and a known **portrait** source image.
   - Main derivative is saved at quality **92**.
   - Zoom derivative fits within the **(3000, 3750)** bounding box at quality **95**.
   - Zoom bounding box stays ≤ `MAX_IMAGE_PIXELS` (25 MP); 3000×3750 = 11.25 MP.

2. Confirm caps are unchanged.
   - `MAX_IMAGE_PIXELS` = 25 MP and `MAX_FILE_SIZE` = 25MB are untouched.
   - Existing WebP / no-EXIF / path-traversal hardening tests still pass.

## Admin Editor — ProductForm

Open the admin product create/edit form.

1. Select a single image file.
   - An editor modal opens holding that file (raw file is **not** added directly).
   - The cropper shows a **4:5** aspect frame with zoom slider, rotate control, and drag-to-pan.

2. Select multiple image files at once.
   - Files are queued; the editor opens one at a time.
   - Confirming advances to the next queued file; the last confirm closes the editor.

3. Confirm a crop.
   - `getCroppedImg` produces a JPEG/PNG `File` with a sensible filename.
   - The blob is added to `formData.image_files` and slots into the existing upload payload unchanged.

4. Cancel a crop.
   - The current file is discarded (nothing added to `image_files`); the editor advances/closes.

5. Validation still applies to editor output.
   - 6-image cap: `images.length + image_files.length > 6` is blocked.
   - Non-image type is rejected.
   - Files over `MAX_IMAGE_SIZE` (25MB) are blocked.
   - Files in the 15–25MB `LARGE_IMAGE_WARNING_SIZE` band trigger the soft-warning dialog.

6. Accessibility / theming.
   - Editor matches the admin theme.
   - Escape dismisses it; focus is trapped inside and restored on close.
   - Control labels render in both `en` and `bg`.

## Storefront — Unified Lightbox

Open a product detail page. Use a product with **multiple images and a `ready` video** (see `frontend/lib/mock-api.ts` fixtures).

1. Slide assembly.
   - `slides[]` follows gallery order: images use `zoom_url` (falling back to `image_url`); the video slide has a poster plus `sources`.
   - `/static/` URLs resolve via `BASE_URL`.

2. Opening.
   - Clicking the hero image opens the lightbox at the correct index.
   - Clicking a thumbnail opens the lightbox at that item's index.
   - Clicking the inline video opens the unified lightbox on the video slide (the old `VideoLightbox` is gone).

3. Navigation.
   - Arrows/swipe page across all images **and** the video within one viewer.
   - Image slides support pan + pinch/scroll zoom via the Zoom plugin.

4. Lazy loading.
   - `zoom_url` and video assets are requested only when their slide is shown, not on page load.

5. Theming & accessibility.
   - Lightbox uses the luxury palette (charcoal backdrop, warm-ivory controls).
   - Labels render localized (`en`/`bg`).
   - Escape and backdrop click close it; focus is trapped and restored.

## Storefront Regression Checks

1. Inline video autoplay-muted behavior is unchanged.
2. Reduced-motion preference is still respected (no autoplay).
3. Product grid still shows poster-only for videos.
4. Only the *enlarge* target moved to the unified lightbox — inline playback is untouched.

## Manual End-to-End

1. Upload a sideways phone photo → confirm it is saved upright.
2. Frame it in the admin editor → confirm the storefront card matches the frame.
3. Open the lightbox → pan-zoom an image, page to the video, then back to an image.
