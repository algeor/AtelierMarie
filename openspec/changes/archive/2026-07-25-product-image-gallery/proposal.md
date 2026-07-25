## Why

Products support exactly one image today: the upload endpoint writes `{product_id}.webp` and overwrites on re-upload, and `products.image_url` holds a single path. Candles sell on their look — front, lit, packaging, scale, lifestyle — so the shop needs a small gallery per product. This change introduces multiple images with an explicit primary, gallery ordering, and per-image management, and retires the single `image_url` field in favor of a proper images table.

## What Changes

- **New `product_images` table** (uuid id, product_id, image_url, thumbnail_url, sort_order, is_primary, created_at) as the source of truth. Up to **6 images per product**.
- **Explicit primary image** (`is_primary` flag, at most one per product enforced by a partial unique index). Product cards/listing show the primary; gallery order is independent of which image is primary.
- **BREAKING (internal): drop `products.image_url`.** All consumers read from the images table. Product responses replace `image_url` with an ordered `images` array plus computed convenience fields `primary_image_url` / `primary_thumbnail_url`.
- **Unique per-image filenames** (`{product_id}_{image_id}.webp` + `_thumb`), so images no longer collide/overwrite. Existing WebP processing (resize, EXIF strip, magic-byte validation, path-traversal guard) is reused per image.
- **New image-management endpoints** (admin): append image, delete image, reorder images, set primary. The old single-image `POST .../image` endpoint is replaced by the append endpoint.
- **Primary invariants:** first uploaded image is primary; deleting the primary promotes another; a product with zero images has `primary_image_url = null` (existing placeholder UI handles it).
- **Migration:** move each product's existing `image_url` into a `product_images` row (primary, sort_order 0), then drop the column.
- **Storefront:** product detail renders a gallery/carousel; product card uses the primary image.
- **Admin:** product form supports multi-upload, reorder, delete, and set-primary.

## Capabilities

### New Capabilities
- `product-image-gallery`: the `product_images` table, per-image processing/filenames, image-management endpoints, primary invariants, the 6-image cap, and the migration off `image_url`.

### Modified Capabilities
- `image-upload`: upload endpoint appends a distinct image (unique filename) instead of overwriting a single `{product_id}.webp`; thumbnail URL is now persisted per image.
- `api-models`: `ProductResponse` replaces `image_url` with `images` + `primary_image_url` / `primary_thumbnail_url`.
- `product-public-api`: list/detail responses carry the images array and primary fields.
- `product-admin-api`: admin product response carries images; admin gains image-management operations.
- `admin-products`: product form supports multiple images (upload, reorder, delete, set primary).
- `product-detail`: detail page renders an image gallery/carousel.
- `product-listing`: product card uses the primary image.

## Impact

- **Backend:** `app/database.py` (new table + partial unique index + migration + **drop `image_url` via table rebuild**; confirm FTS triggers don't reference `image_url` — they don't), `app/services/image_service.py` (per-image filenames), new/expanded `app/services/product_image_service.py`, `app/routes/admin.py` (new endpoints, replace single-image route), `app/models/products.py` (response reshape), `app/services/product_service.py` (assemble images into responses).
- **Frontend:** product detail gallery component, `ProductCard` (primary image), admin multi-image manager UI in `ProductForm.tsx`, `lib/types.ts` (images shape), `lib/api*.ts`, `lib/mock-api.ts`, i18n.
- **BREAKING for API consumers:** `image_url` removed from product responses — the frontend must switch to `primary_image_url` / `images` in the same change.
- **Not affected:** pricing, cart totals, checkout, orders.
