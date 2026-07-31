# Products, Taxonomy, Discounts, And Media

Use this when touching product pages, product admin, search/filtering, discounts, images, or video.

## Mental Model

A product is not just name + price.

Current product data includes:

- bilingual names and descriptions
- safety/care/compliance fields
- price and active discount fields
- stock and weight
- managed taxonomy: product type, category, labels
- image gallery with primary image, thumbnails, zoom versions
- optional video with transcode status
- active/featured flags

## Main Backend Files

- `app/models/products.py`: product request/response contracts.
- `app/routes/products.py`: public listing/detail endpoints.
- `app/routes/admin.py`: admin product CRUD, CSV import, image/video endpoints.
- `app/services/product_service.py`: product CRUD, search, discounts, taxonomy validation.
- `app/services/taxonomy_service.py`: product types, categories, labels.
- `app/services/product_image_service.py`: image gallery rows and primary image logic.
- `app/services/image_service.py`: validation, resize, WebP, thumbnail/zoom derivatives.
- `app/services/product_video_service.py`: video queue, state, lease, public attachment.
- `app/services/video_service.py`: ffprobe validation, ffmpeg transcode, poster extraction.
- `app/services/pricing.py`: effective price rules.

## Main Frontend Files

- `frontend/components/products/*`: product cards, listing, detail, gallery, price display, reactions/comments.
- `frontend/components/admin/ProductForm.tsx`: product create/edit, taxonomy, discounts, media.
- `frontend/components/admin/ImageCropEditor.tsx`: image framing/crop editor.
- `frontend/components/admin/TaxonomyManager.tsx`: managed taxonomy UI.
- `frontend/lib/types.ts`: product/media/taxonomy types.
- `frontend/lib/media.ts`: media URL helpers.
- `frontend/lib/mock-api.ts`: product mock data.

## Product API Rules

- Public list/detail endpoints return locale-resolved fields.
- Admin endpoints expose bilingual fields and inactive products.
- Frontend types must mirror Pydantic models.
- Product list responses include pagination.
- Product detail should not require auth.
- Admin create/update requires admin auth.

## Bilingual Content Rules

- Store both English and Bulgarian content where the model supports it.
- Public APIs resolve to the requested locale with fallback.
- Admin UI should show both languages side by side where practical.
- Translation stale flags exist so admins can see when a language needs attention.
- Search should respect locale where supported.

## Taxonomy Rules

Managed taxonomy replaced hardcoded category pills.

There are three managed term groups:

- product types
- categories
- labels

Rules:

- Do not hardcode product categories in frontend filters.
- Validate product type/category/labels against managed taxonomy.
- Deleting a used taxonomy value should be guarded. Deactivate instead when needed.
- Product listing filters combine selected taxonomy slugs.
- Existing legacy `category` still exists for compatibility. Prefer the managed fields for new work.

## Discount Rules

- `price_cents` is the base price.
- `effective_price_cents` is what the customer pays when a discount is active.
- Discount windows are evaluated server-side.
- Checkout snapshots the effective price into `order_items.price_cents`.
- Do not recompute old order item prices from current product discounts.
- Campaigns bulk-apply product discounts, but the charged price still comes from the same pricing helper.

## Image Rules

- Products can have multiple images.
- Exactly one image should be primary.
- Product cards use the primary thumbnail/image.
- Detail pages use the gallery.
- Uploads are validated, orientation-fixed, converted to WebP, and generate derivatives.
- High-resolution `zoom_url` exists for lightbox/inspection.
- Admin crop/rotate/zoom bakes framing into pixels. Do not store crop metadata and expect the public UI to recreate it.
- Deleting images should clean up derived files when safe.

## Video Rules

- A product can have one video row.
- Uploads are queued, then transcoded.
- States are `queued`, `transcoding`, `ready`, `failed`.
- Public product responses should only expose usable ready video data.
- Admin can inspect/delete/update sort order.
- ffmpeg/ffprobe paths come from config.
- Do not block normal product browsing because a video transcode failed.

## Reactions And Comments

Product social features are lightweight.

- Reactions are session-scoped.
- Comments support anonymous/session and logged-in identity.
- Comment body is sanitized.
- Admin can moderate/delete comments.
- Rate limits protect comment/reaction spam.

## Safe Change Checklist

- Updated Pydantic model and frontend type.
- Updated mock API if public/admin response changed.
- Kept money in cents.
- Kept product IDs as strings.
- Tested public list/detail and admin create/update.
- Tested checkout if price, discount, stock, or product active logic changed.
- Tested image/video upload paths if media behavior changed.

