# Product Media Editor And Lightbox

Use this when touching product image crop/rotate/zoom, image quality, `zoom_url`, or the product media lightbox.

Source change: `openspec/changes/archive/2026-07-31-product-media-editor-and-lightbox`.

## Mental Model

- Admin picks the final frame before upload.
- The backend stores finished pixels, not crop settings.
- The storefront shows those pixels everywhere.
- Images and video open in one shared lightbox.

The important decision: crop/rotate/zoom is baked into the uploaded image. There is no crop metadata to replay later.

## Main Files

### Admin Frontend

- `frontend/components/admin/ProductForm.tsx`: owns image selection, crop editor queue, upload payload.
- `frontend/components/admin/ImageCropEditor.tsx`: crop/rotate/zoom UI.
- `frontend/lib/cropImage.ts`: canvas helper that exports the cropped image as a file.
- `frontend/messages/en.json`, `frontend/messages/bg.json`: editor and lightbox labels.

### Storefront Frontend

- `frontend/components/products/ProductGallery.tsx`: gallery, mixed media ordering, `yet-another-react-lightbox`.
- `frontend/lib/media.ts`: resolves media URLs.
- `frontend/lib/types.ts`: product image/video types.

### Backend

- `app/services/image_service.py`: EXIF orientation, resize, WebP output, derivative quality.
- `app/services/product_image_service.py`: gallery rows, primary image, ordering, delete cleanup.
- `app/services/product_video_service.py`: video row state attached to products.
- `app/routes/admin.py`: admin upload endpoints.
- `app/models/products.py`: product media response contracts.

## Admin Image Flow

```text
Admin selects image
  -> ProductForm opens ImageCropEditor
  -> editor locks crop to 4/5 storefront aspect
  -> admin drags, zooms, rotates
  -> cropImage exports a new image file from canvas
  -> ProductForm uploads that file through existing FormData
  -> backend validates and processes it like any other image
```

Cancel means discard the selected file. Confirm means upload the cropped file.

Multiple selected files are handled one at a time. Keep that predictable. It prevents unclear partial uploads.

## Backend Image Flow

```text
image bytes
  -> Pillow opens and verifies
  -> ImageOps.exif_transpose makes phone photos upright
  -> metadata is stripped
  -> main WebP is written
  -> thumbnail WebP is written
  -> zoom WebP is written
  -> URLs are returned for DB storage
```

Current derivative intent:

| Derivative | Current target | Purpose |
|---|---:|---|
| thumbnail | 400x500, q80 | Product cards and lists. |
| main image | 2000x2500, q92 | Product detail hero/gallery. |
| zoom image | 3000x3750, q95 | Lightbox detail inspection. |

Quality direction from the archived change:

- Main image quality is intentionally higher than the old baseline.
- Zoom derivative is intentionally larger and sharper than the old baseline.
- `MAX_IMAGE_PIXELS` and upload size caps stay as safety rails.

## Storefront Lightbox Flow

`ProductGallery.tsx` builds one ordered media list.

```text
product images + ready video
  -> galleryItems sorted by sort_order
  -> yet-another-react-lightbox slides
  -> Lightbox opens at clicked item index
```

Image slide mapping:

```text
{ zoom_url, image_url } -> src = zoom_url ?? image_url
```

Video slide mapping:

```text
{ video_url, poster_url } -> video slide with controls and poster
```

The lightbox uses `yet-another-react-lightbox` with image zoom and video support. Do not bring back separate custom modals for image zoom and video enlarge.

## Rules That Save Time

- Keep the crop aspect aligned with storefront cards: `4/5`.
- Do not add DB columns for crop, zoom, focal point, or rotation unless the product owner asks for non-destructive re-editing.
- Do not expect old originals to exist. Re-crop means upload again.
- Always fix EXIF orientation before stripping metadata.
- Keep `zoom_url` optional. Legacy/external images may not have it.
- Lightbox image source must fall back to `image_url` when `zoom_url` is missing.
- One media viewer means one keyboard/focus/close behavior for images and video.
- This area must not affect cart, checkout, pricing, orders, or auth.

## Common Traps

| Symptom | Check First |
|---|---|
| Product photo is sideways | `ImageOps.exif_transpose` in `image_service.py`. |
| Card framing differs from editor | Crop aspect in `ImageCropEditor.tsx` and card aspect in product UI. |
| Lightbox image looks soft | Missing `zoom_url`, wrong media URL resolution, or derivative quality/dimensions. |
| Video opens in a separate modal | `ProductGallery.tsx` should open the shared lightbox at the video slide. |
| Tests pass but manual gallery is weak | Mock product may lack multiple images plus a ready video. |
| Crop upload bypasses size checks | `ProductForm.tsx` should feed the exported file through the existing upload validation. |

## What To Test

Backend:

- EXIF-oriented phone image saves upright.
- WebP output has no EXIF metadata.
- Main, thumbnail, and zoom derivatives are written.
- Zoom derivative stays under pixel safety limits.
- Legacy image rows with `zoom_url = null` still work.

Frontend admin:

- Selecting an image opens the crop editor.
- Confirm adds the exported file to the upload payload.
- Cancel adds nothing.
- Existing image count limit and size warnings still apply.
- Keyboard close/focus behavior does not strand the user.

Frontend storefront:

- Mixed images and video render in gallery order.
- Clicking any item opens the lightbox at the correct index.
- Image slides use `zoom_url` with `image_url` fallback.
- Video plays inside the same lightbox flow.
- Escape/backdrop/close controls work.

## Good Change Pattern

1. Change the smallest file that owns the behavior.
2. Update types or mocks only if the response shape changed.
3. Keep crop output going through the existing backend upload path.
4. Run the narrow media tests first.
5. Manually try one ugly real-world image: portrait phone photo, off-center subject, and large file.

Related docs:

- [02-product-media-pipeline.md](02-product-media-pipeline.md)
- [01-product-catalog.md](01-product-catalog.md)
- [../features/01-products-taxonomy-media.md](../features/01-products-taxonomy-media.md)
- [../reference/test-map.md](../reference/test-map.md)
