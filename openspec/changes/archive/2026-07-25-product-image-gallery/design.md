## Context

Images are single per product today:

```
products.image_url (TEXT, nullable)   → one main image path
image_service.process_image()         → writes {id}.webp + {id}_thumb.webp
                                         (resize 1200×1500 / 400×500, EXIF strip,
                                          magic-byte validate, path-traversal guard)
POST /v1/admin/products/{id}/image     → overwrites the single file, sets image_url
Frontend: ProductCard + detail read product.image_url; thumb derived by convention
```

The filename `{product_id}.webp` is the hard blocker: a second upload overwrites the first. There is no image entity, no ordering, no primary concept beyond "the one file."

## Goals / Non-Goals

**Goals:**
- Up to 6 images per product with stable ordering and an explicit primary.
- Reuse the hardened processing pipeline (validation, resize, EXIF, traversal guard) per image.
- Clean data model: images live in their own table; `products.image_url` is removed.
- Storefront gallery on detail; primary image on cards.

**Non-Goals:**
- Video, 360° spins, or zoom/lightbox beyond a basic gallery.
- CDN / responsive art-direction beyond existing next/image sizing.
- Alt-text per image localization (use product name as alt for now).

## Decisions

### 1. `product_images` table with a partial unique primary index
```
product_images(
  id            TEXT PRIMARY KEY,          -- uuid4 hex
  product_id    TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  image_url     TEXT NOT NULL,
  thumbnail_url TEXT NOT NULL,             -- now persisted (was derived by convention)
  sort_order    INTEGER NOT NULL DEFAULT 0,
  is_primary    INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL
)
CREATE INDEX idx_product_images_product ON product_images(product_id, sort_order);
CREATE UNIQUE INDEX idx_product_images_one_primary
  ON product_images(product_id) WHERE is_primary = 1;
```
The partial unique index enforces **at most one primary per product** at the DB level. The service guarantees **at least one** primary whenever ≥1 image exists.

### 2. Explicit primary flag, independent of order
`is_primary` is set explicitly (chosen decision). Reordering the gallery does not change which image is primary. Card/listing/thumbnail reads use the primary; the detail gallery renders all images in `sort_order` with the primary marked.

### 3. Drop `products.image_url`; responses expose `images` + computed primary
`ProductResponse` / `ProductAdminResponse` replace `image_url` with:
- `images`: ordered list of `{id, image_url, thumbnail_url, sort_order, is_primary}`
- `primary_image_url`: the primary image's URL, or `null` if no images
- `primary_thumbnail_url`: the primary thumbnail, or `null`

Convenience primary fields keep card rendering a one-field read (replacing `image_url`) while `images` powers the gallery. This is a **breaking response change**; the frontend switches in the same change.

### 4. Unique per-image filenames
`{product_id}_{image_id}.webp` and `{product_id}_{image_id}_thumb.webp`. Both `product_id` (slug allowlist) and `image_id` (uuid hex) are safe for path construction; the existing `resolve().relative_to(base_dir)` guard is retained. No more overwrite-by-name.

### 5. Primary lifecycle
- **First image** uploaded to a product → `is_primary = 1`, `sort_order = 0`.
- **Append** → `is_primary = 0`, `sort_order = max+1`.
- **Set primary** (`PATCH .../{image_id}/primary`) → in one transaction clear the old primary and set the new (satisfies the partial unique index).
- **Delete primary** → promote the remaining image with the lowest `sort_order` to primary. If it was the last image, the product has no primary (`null`).
- **6-image cap** → append returns 409 (or 422) when the product already has 6 images.

### 6. Endpoints (admin, `require_admin`)
- `POST /v1/admin/products/{id}/images` — append one image (multipart); returns the created image. Replaces the old single-image `POST .../image`.
- `DELETE /v1/admin/products/{id}/images/{image_id}` — delete row + files; promote primary if needed.
- `PATCH /v1/admin/products/{id}/images/reorder` — body `{ordered_ids: [...]}` → assign `sort_order`.
- `PATCH /v1/admin/products/{id}/images/{image_id}/primary` — set primary.

### 7. Migration off `image_url`
Idempotent, on startup:
1. Create `product_images` table + indexes.
2. For each product with non-null `image_url`, insert a row: `image_url` = existing value, `thumbnail_url` = derived `{id}_thumb.webp` convention, `is_primary = 1`, `sort_order = 0`, `id` = deterministic-from-product or uuid.
3. Drop `products.image_url` (SQLite ≥ 3.35 `ALTER TABLE DROP COLUMN`, or via the existing `products_new` rebuild path — remove `image_url` from the rebuilt schema and copy list). FTS triggers do not reference `image_url`, so they are unaffected.
4. Guard so the seed runs once (skip if `product_images` already populated).

## Risks / Trade-offs

- **Dropping a column is destructive** → migration copies data into `product_images` first; the value is recoverable from the new row. Rollback keeps the images table (harmless) but reverting code that still expects `image_url` would need the column back — call this out; forward-only is preferred.
- **Breaking API response** (`image_url` gone) → frontend + mock-api updated in the same change; a grep for `image_url` consumers is a task.
- **Orphaned files on delete** → delete the DB row and the two WebP files in the same operation; if file unlink fails, log and continue (DB is source of truth).
- **Primary invariant races** (two concurrent set-primary) → do the clear+set in a single transaction; the partial unique index is the backstop.
- **Cap enforcement race** (two concurrent appends at 5 images) → count-and-insert inside a transaction; worst case a 7th slips in — acceptable, admin-only, low concurrency.
- **Four+ changes touch `admin-products` and product responses** → D's form/response deltas are additive requirements layered on the prior changes; sequence D last so its response reshape lands after A/B/C field additions.

## Migration Plan

1. Ship table + endpoints + migration + response reshape + frontend together (breaking response requires atomic FE/BE landing).
2. Migration runs once on startup: seed images, drop `image_url`.
3. Rollback: forward-only preferred. If necessary, re-add `image_url` and backfill from each product's primary image URL.

## Open Questions

- CSV import currently accepts an `image_url` column. Proposed: keep accepting it as "create one primary image" for that product (append semantics), or drop it from CSV. Defaulting to: keep, treated as the primary image. Marked optional in tasks.
- Per-image alt text / captions — deferred (use product name as alt).
