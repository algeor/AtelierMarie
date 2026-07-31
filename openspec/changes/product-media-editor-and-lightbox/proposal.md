## Why

The owner can upload product photos but has **no control over how they are framed or how crisp they end up**, and the store's media viewers are fragmented. Three concrete pains:

1. **No framing control.** Uploaded photos are shoehorned into a fixed `4/5` `object-cover` card (`ProductImage.tsx`), which center-crops. A candle sitting off-center in a landscape shot gets half cut off, and the admin can't choose what to keep, rotate a sideways shot, or zoom the subject to fill the frame.
2. **Orientation bug.** `image_service.process_image` strips EXIF but never applies `exif_transpose`. Phone photos carry an orientation flag; stripping it *without* rotating the pixels makes portrait shots appear **sideways**. (The `image-upload` spec's "EXIF metadata stripped" requirement is satisfied literally, but produces wrong-way-up images.)
3. **Fragmented, weak viewers.** The storefront has a custom fullscreen `object-contain` zoom modal (`ProductGallery.tsx`) that **can't pan or pinch into detail**, plus a separate `VideoLightbox.tsx`. Images and video open in two different modals; a shopper can't page from a photo to the video to the next photo in one flow, and can't inspect fine detail (wax texture, label print).

This change gives the admin a **crop/rotate/zoom editor** before upload, fixes the orientation bug, sharpens the stored derivatives, and replaces both custom viewers with a **single media lightbox** (`yet-another-react-lightbox`) that pans/pinch-zooms images and plays video in **one navigable carousel**. All admin/customer-facing — no impact on cart, checkout, orders, or pricing.

## What Changes

- **Admin image editor (`react-easy-crop`).** When an admin selects an image in `ProductForm`, an editor opens with **crop + rotate + zoom + drag**, locked to the storefront's `4/5` aspect. On confirm, the framed result is exported to a blob (via a canvas helper) and *that* is what uploads — WYSIWYG, framed exactly as it will appear. Cancel discards the file. The existing 6-image limit, ordering, primary-image, and 15–25MB soft-warning / >25MB block behavior are preserved; the editor sits in front of them.
- **Fix EXIF orientation (backend).** `process_image` applies `ImageOps.exif_transpose` to upright the pixels **before** resizing/stripping. Output stays EXIF-free (metadata still removed) but visually correct. The admin's manual rotate is layered on top as an override.
- **Sharpen stored derivatives.** Bump main WebP quality `88 → 92`; bump the zoom derivative to `3000×3750 @ q95` (from `2400×3000 @ q90`) so there are enough pixels to pan into fine detail. Thumbnail unchanged. `MAX_IMAGE_PIXELS` (25 MP safety ceiling) unchanged — `3000×3750 = 11.25 MP`, well under it. The 25MB upload cap is unchanged (it was never the quality lever).
- **Unified media lightbox (`yet-another-react-lightbox`).** Replace the custom zoom modal *and* `VideoLightbox.tsx` with one lightbox fed by the gallery's existing ordered `galleryItems[]` (images + video, by `sort_order`). Images get **pan + pinch zoom** (Zoom plugin) sourced from `zoom_url`; the video slide plays with sound + controls (Video plugin). Arrow keys / swipe / thumbnail-click **navigate across the entire set** — photo → video → photo — in one flow. Themed to the luxury palette; keyboard/focus/reduced-motion/i18n ported into YARL's config.

## Capabilities

### New Capabilities
<!-- None — this change modifies existing capabilities only. -->

### Modified Capabilities
- `admin-products`: product image upload gains a crop/rotate/zoom editor (react-easy-crop) that bakes framing into the uploaded image, locked to the `4/5` storefront aspect.
- `image-upload`: image processing applies EXIF orientation (`exif_transpose`) before stripping metadata; main/zoom WebP quality and zoom dimensions increased.
- `product-image-gallery`: the click-to-zoom lightbox becomes a unified media carousel (yet-another-react-lightbox) with pan/pinch zoom on images and navigation across all images and the video in one sequence.
- `product-video`: the video "enlarge" behavior now opens inside the shared media carousel (navigable to/from adjacent images) instead of a standalone `VideoLightbox`.

## Related Changes

- **`crisp-zoom-images` (complete, not yet archived).** This change builds directly on its `zoom_url` derivative and click-to-zoom lightbox. It **modifies** that lightbox: the custom `object-contain` modal it added is replaced by YARL with real pan/pinch zoom. The `zoom_url` derivative is retained and its dimensions/quality raised here.
- **`add-product-video` (complete, not yet archived).** This change **absorbs** its `VideoLightbox` into the unified carousel. The video's inline autoplay-muted behavior and `sort_order` insertion into the gallery are unchanged; only the *enlarge* target changes (shared lightbox instead of standalone). Whichever archives relative to this change, the `product-video` "Video plays inline muted and enlarges with sound" requirement is the coordination point.

## Impact

- **Backend:** `app/services/image_service.py` — add `ImageOps.exif_transpose` at the top of processing; raise `_MAIN_QUALITY` to 92, `_ZOOM_MAX_SIZE` to `(3000, 3750)`, `_ZOOM_QUALITY` to 95. No schema, model, or route changes (framing is baked into pixels — no new fields).
- **Frontend (admin):** `frontend/components/admin/ProductForm.tsx` — integrate `react-easy-crop` editor into the image-select flow; new `getCroppedImg` canvas helper; new i18n strings for editor controls. Add `react-easy-crop` dependency.
- **Frontend (storefront):** `frontend/components/products/ProductGallery.tsx` — replace the inline zoom modal and the `VideoLightbox` invocation with `yet-another-react-lightbox` (Zoom + Video + Thumbnails plugins) fed by `galleryItems[]`. **Delete** `frontend/components/products/VideoLightbox.tsx`. Add `yet-another-react-lightbox` dependency. Port focus/reduced-motion/i18n labels into YARL config; theme via CSS variables.
- **No impact** on cart, checkout, order snapshots, pricing, auth, the product API contract (no new fields), or the DB schema.
- **Tests:** editor exports a `4/5`-framed blob that is what gets uploaded; sideways EXIF-oriented input is saved upright; main/zoom quality and zoom dimensions match the new constants; lightbox renders images and video from one ordered set and navigates across them; pan/zoom uses `zoom_url` with `image_url` fallback; keyboard/close behavior preserved.
