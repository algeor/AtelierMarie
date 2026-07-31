# Tasks — Product Media Editor & Unified Lightbox

## 1. Backend — EXIF orientation fix (`app/services/image_service.py`)

- [x] 1.1 Import `ImageOps` from PIL; in `process_image`, after the image is opened/verified and loaded (and before the RGB-conversion/resize steps), apply `img = ImageOps.exif_transpose(img)` to upright the pixels
- [x] 1.2 Confirm metadata is still absent on WebP output (existing behavior) — no EXIF written; add/adjust a comment noting orientation is baked into pixels
- [x] 1.3 Verify the manual-rotate-from-editor path is unaffected (editor blobs carry no EXIF, so `exif_transpose` is a no-op on them)

## 2. Backend — quality/dimension bump (`app/services/image_service.py`)

- [x] 2.1 Raise `_MAIN_QUALITY` from 88 to 92
- [x] 2.2 Raise `_ZOOM_MAX_SIZE` from `(2400, 3000)` to `(3000, 3750)` and `_ZOOM_QUALITY` from 90 to 95
- [x] 2.3 Confirm `MAX_IMAGE_PIXELS` (25 MP) and `MAX_FILE_SIZE` (25MB) are left unchanged (11.25 MP zoom < ceiling)
- [x] 2.4 Update any docstring/comment referencing the old dimensions/quality

## 3. Admin editor — dependency & canvas helper (`frontend/`)

- [x] 3.1 Add `react-easy-crop` to `frontend/package.json` (npm install)
- [x] 3.2 Create a `getCroppedImg(imageSrc, croppedAreaPixels, rotation)` canvas helper (adapt from react-easy-crop docs) returning a `Blob`/`File`; place it near `ProductForm` or in `frontend/lib/`
- [x] 3.3 Ensure the helper outputs a JPEG/PNG `File` with a sensible filename so it slots into the existing `image_files` upload payload unchanged

## 4. Admin editor — ProductForm integration (`frontend/components/admin/ProductForm.tsx`)

- [x] 4.1 On image file selection, instead of adding the raw file directly, open an editor modal holding the selected file (one file at a time if multiple selected — queue them)
- [x] 4.2 Render `<Cropper>` with `aspect={4/5}`, `zoom`, and `rotation` state + controls (zoom slider, rotate button/slider, drag to pan)
- [x] 4.3 On confirm: call `getCroppedImg`, add the resulting blob/File to `formData.image_files`, close the editor; advance to the next queued file if any
- [x] 4.4 On cancel: discard the current file, do not add it; advance/close
- [x] 4.5 Ensure the exported blob passes through the existing validation: 6-image cap (`images.length + image_files.length > 6`), type check, `MAX_IMAGE_SIZE` (25MB) block, and the 15–25MB (`LARGE_IMAGE_WARNING_SIZE`) soft-warning dialog
- [x] 4.6 Style the editor with Tailwind to match the admin theme; make it keyboard-dismissible and focus-managed
- [x] 4.7 Add i18n strings for editor controls (zoom, rotate, confirm, cancel, aspect hint) to `frontend/messages/en.json` + `bg.json`

## 5. Storefront — unified lightbox dependency (`frontend/`)

- [x] 5.1 Add `yet-another-react-lightbox` to `frontend/package.json` (npm install); note it ships Zoom, Video, Thumbnails plugins
- [x] 5.2 Import the base lightbox CSS and plugin CSS where the gallery renders

## 6. Storefront — replace modals with unified lightbox (`frontend/components/products/ProductGallery.tsx`)

- [x] 6.1 Build a `slides[]` array from the existing ordered `galleryItems[]`: image → `{type:"image", src: zoom_url ?? image_url, alt: name}`; video → `{type:"video", poster: poster_url, sources:[{src: video_url, type}]}` (resolve `/static/` URLs via `BASE_URL`)
- [x] 6.2 Replace the inline `isZoomOpen` `object-contain` modal (current lines ~246–279) with `<Lightbox>` using Zoom + Video + Thumbnails plugins
- [x] 6.3 Wire the hero click and thumbnail clicks to open the lightbox at the correct `index` (map selected item → slide index)
- [x] 6.4 Replace the `VideoLightbox` invocation (the `lightboxVideo` path) so clicking the inline video opens the unified lightbox on the video slide
- [x] 6.5 Configure Zoom plugin for pan + pinch/scroll on image slides; confirm it uses the `zoom_url` source with `image_url` fallback
- [x] 6.6 Confirm lazy loading: `zoom_url`/video assets are requested only when their slide is shown, not on page load
- [x] 6.7 Pass localized `labels` to the lightbox; add any new i18n strings to `en.json` + `bg.json`
- [x] 6.8 Theme the lightbox via CSS variables to the luxury palette (charcoal backdrop, warm-ivory controls) to match the retired modals
- [x] 6.9 Preserve/verify keyboard + focus behavior (dialog, focus trap, Esc/backdrop close) via YARL config

## 7. Storefront — cleanup

- [x] 7.1 Delete `frontend/components/products/VideoLightbox.tsx` and remove its imports/usages
- [x] 7.2 Remove now-dead state/handlers in `ProductGallery.tsx` (custom `isZoomOpen` modal markup, `zoomFailed` handling if superseded, `lightboxVideo` if replaced), keeping inline-autoplay behavior intact
- [x] 7.3 Confirm inline video autoplay-muted / reduced-motion / grid-poster-only behavior is unchanged (only the *enlarge* target moved to the unified lightbox)

## 8. Tests — backend

- [x] 8.1 Test that an image with an EXIF orientation flag is saved upright (compare output dimensions/orientation to expected upright result)
- [x] 8.2 Test main derivative saved at quality 92 and zoom at `(3000, 3750)` bounding box / quality 95 (dimensions for a known landscape and portrait input)
- [x] 8.3 Test zoom bounding box stays ≤ `MAX_IMAGE_PIXELS`; confirm cap constants unchanged
- [x] 8.4 Confirm existing WebP/no-EXIF/path-traversal tests still pass with the new constants

## 9. Tests — frontend

- [x] 9.1 Editor: selecting a file opens the cropper; confirm exports a blob added to `image_files`; cancel adds nothing
- [x] 9.2 Editor: exported blob is subject to the 6-image cap and 15–25MB warning / >25MB block
- [x] 9.3 Lightbox: renders slides from a mixed image+video product in gallery order; opening on a given item sets the right index
- [x] 9.4 Lightbox: navigating advances across images and the video within one viewer; image slide uses `zoom_url` with `image_url` fallback
- [x] 9.5 Lightbox: closes on Escape/backdrop; focus is trapped and restored
- [x] 9.6 Update `frontend/lib/mock-api.ts` fixtures if needed so a product carries multiple images + a `ready` video for manual/lightbox testing

## 10. Verification

- [ ] 10.1 `make lint` and `make format` clean
- [x] 10.2 `make test-backend` and `make test-frontend` green
- [ ] 10.3 Manual: upload a sideways phone photo → saved upright; frame it in the editor → storefront card matches; open lightbox → pan-zoom an image, page to the video, back to an image
