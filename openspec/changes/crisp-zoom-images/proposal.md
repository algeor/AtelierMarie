## Why

Product photos look soft on modern (retina/hi-dpi) screens, and customers can't zoom in to inspect detail (wax texture, label, finish). The cause is not the upload path — it's that every image is downscaled to a single 1200×1500 WebP and served as one file to every screen size. On a 2× display the browser upscales that 1200px file, so it reads as blurry, and there is no higher-resolution variant to zoom into.

The owner wants uploaded photos to appear **as crisp as the original** and to support **click-to-zoom** on the product page. This change raises the (irrelevant-to-quality) upload cap, stores a high-resolution zoom derivative, sharpens the display path, and adds a zoom UI — all admin/customer-facing, with no impact on cart, checkout, orders, or pricing.

## What Changes

- **Raise the upload size cap 5MB → 25MB** so full-resolution phone/camera photos are accepted. This is enforced in two backend places (`image_service.MAX_FILE_SIZE` and the `admin.py` streaming chunk guard) plus the Nginx `client_max_body_size` at deploy time. The 25-megapixel decompression-bomb cap (`MAX_IMAGE_PIXELS`) is **left unchanged** as a safety ceiling.
- **Generate a third "zoom" derivative** (~2400×3000, WebP quality 90) alongside the existing main and thumbnail. Zoom is a downscaled derivative, **not** the byte-for-byte original — visually indistinguishable but bandwidth-controlled and EXIF-stripped like the others.
- **Sharpen the main derivative**: bump from 1200×1500 q85 to ~2000×2500 q88 so the on-page hero is crisp on 2× displays without needing the zoom asset.
- **Add `zoom_url` to the image data model** — new `product_images.zoom_url` column and `zoom_url` on the `ProductImage` object in the product API. **No migration/backfill** — the project is not live yet, so the schema is added directly to the fresh-DB definition.
- **Frontend display**: the gallery hero serves the sharper main image (retina-crisp), and a **click-to-zoom lightbox** loads the `zoom_url` asset on demand (lazy — not fetched until the user zooms).
- **Admin upload soft-warning**: when an admin selects a file **between 15MB and 25MB**, a confirmation dialog warns that the image is large and asks to proceed. Files **over 25MB** are blocked client-side before upload (backend still hard-rejects as defense-in-depth).

## Capabilities

### New Capabilities
<!-- None — this change modifies existing capabilities only. -->

### Modified Capabilities
- `image-upload`: file size limit raised to 25MB; resize step produces **three** sizes (thumb, main, zoom) with main sharpened; WebP quality settings updated; new zoom derivative requirement.
- `api-models`: each image object in `ProductResponse.images` gains a `zoom_url` field.
- `product-image-gallery`: gallery hero is retina-crisp; new click-to-zoom lightbox loading the zoom derivative on demand.
- `admin-products`: admin image upload shows a soft-warning confirm dialog for files 15–25MB and blocks files over 25MB before upload.

## Related Changes

- **`add-product-video`** (concurrent, complementary — adds one self-hosted *video* per product, displayed inside this same gallery). Shared surfaces to coordinate:
  - **Nginx `client_max_body_size`** — this change sets `25m` for image uploads; `add-product-video` needs a far larger cap (~100–200MB raw video). Set the large cap **per-location** on the video upload route only, keeping the `25m` image limit intact — don't let a single global value blur the two.
  - **Gallery component** — both modify `ProductGallery.tsx` (this change sharpens the hero + adds the zoom lightbox; the other interleaves a video slide by `sort_order`). Whichever lands second merges, not overwrites.
  - **Lightbox reuse** — the zoom lightbox built here (dialog role, focus trap, Esc/backdrop close, lazy asset load) should be the shared base the video change's `VideoLightbox` reuses.
  - **Fresh-DB schema** — both edit `app/database.py` with "no migration, not live yet" (the `zoom_url` column here vs. a new `product_videos` table there). Same file, independent additions.
  - **mock-api fixtures** — both add media to `frontend/lib/mock-api.ts`; keep one product carrying both a `zoom_url` image set and a `ready` video.

## Impact

- **Backend:** `app/services/image_service.py` (size cap, third derivative, main dimensions/quality), `app/routes/admin.py` (chunk-guard cap, response includes `zoom_url`), `app/database.py` (`product_images.zoom_url` column — fresh schema only, no rebuild/backfill), `app/models/products.py` (`ProductImage.zoom_url`).
- **Frontend:** `frontend/components/products/ProductGallery.tsx` (retina hero + zoom lightbox), a new lightbox component, `frontend/components/admin/*` (upload soft-warning dialog), `frontend/lib/types.ts` (`zoom_url`), `frontend/lib/mock-api.ts`, `frontend/messages/en.json` + `bg.json` (warning + zoom labels).
- **Deploy:** bump Nginx `client_max_body_size` to `25m` (referenced by the `image-upload` spec; not committed in-repo).
- **No impact** on cart, checkout, order snapshots, pricing, auth, or the public product *listing* contract beyond the additive `zoom_url` field.
- **Tests:** 25MB accept / >25MB reject; three-derivative generation and dimensions; `zoom_url` present in API responses; frontend 15–25MB warning + >25MB block; lightbox renders zoom asset.
