## 1. Database schema & migration (`app/database.py`)

- [x] 1.1 Create `product_images` table (id, product_id FK ON DELETE CASCADE, image_url, thumbnail_url, sort_order, is_primary, created_at)
- [x] 1.2 Add index `(product_id, sort_order)` and partial unique index on `(product_id) WHERE is_primary = 1`
- [x] 1.3 Idempotent migration: for each product with non-null `image_url`, insert a primary row (sort_order 0, thumb by convention)
- [x] 1.4 Drop `products.image_url` (ALTER DROP COLUMN or `products_new` rebuild path — remove from schema + copy list); confirm FTS triggers don't reference it
- [x] 1.5 Guard migration to run once; verify re-run creates no duplicates

## 2. Image processing (`app/services/image_service.py`)

- [x] 2.1 Change filename scheme to `{product_id}_{image_id}.webp` + `_thumb`; return both URLs
- [x] 2.2 Keep magic-byte validation, resize, EXIF strip, and path-traversal guard (validate product_id slug + image_id uuid)

## 3. Image service (`app/services/product_image_service.py`)

- [x] 3.1 `list_images(product_id)` ordered by sort_order
- [x] 3.2 `add_image(product_id, bytes)` — enforce 6-cap (409), first image → primary, else sort_order = max+1
- [x] 3.3 `delete_image(product_id, image_id)` — remove row + unlink files; promote lowest-sort_order to primary if the primary was deleted
- [x] 3.4 `reorder_images(product_id, ordered_ids)` — validate set membership, set sort_order (primary unchanged)
- [x] 3.5 `set_primary(product_id, image_id)` — clear old + set new in one transaction
- [x] 3.6 Helper to assemble `images`, `primary_image_url`, `primary_thumbnail_url` for responses

## 4. Models (`app/models/products.py`)

- [x] 4.1 Add `ProductImage` schema (id, image_url, thumbnail_url, sort_order, is_primary)
- [x] 4.2 `ProductResponse` / `ProductAdminResponse`: remove `image_url`; add `images`, `primary_image_url`, `primary_thumbnail_url`
- [x] 4.3 Remove `image_url` from `CreateProductRequest`/`UpdateProductRequest` (images managed via dedicated endpoints)

## 5. Routes (`app/routes/admin.py`)

- [x] 5.1 Replace `POST .../{id}/image` with `POST /v1/admin/products/{id}/images` (append, 201)
- [x] 5.2 `DELETE /v1/admin/products/{id}/images/{image_id}`
- [x] 5.3 `PATCH /v1/admin/products/{id}/images/reorder`
- [x] 5.4 `PATCH /v1/admin/products/{id}/images/{image_id}/primary`

## 6. Product service (`app/services/product_service.py`)

- [x] 6.1 Assemble images + primary fields into public and admin product reads (list + detail)
- [x] 6.2 Remove `image_url` from create/update persistence

## 7. Frontend

- [x] 7.1 `lib/types.ts`: add `ProductImage`, replace `image_url` with `images` + `primary_image_url` (+ thumb)
- [x] 7.2 `ProductCard`: use `primary_image_url` (placeholder when null)
- [x] 7.3 Product detail: gallery/carousel (primary large + selectable thumbnails in order)
- [x] 7.4 `ProductForm.tsx`: multi-image manager — upload (cap 6), reorder, delete, set primary; wire to new endpoints
- [x] 7.5 `lib/api*.ts` + `lib/mock-api.ts`: image-management calls + multi-image fixtures; remove `image_url` usages
- [x] 7.6 i18n strings (gallery, set primary, max reached) in `en.json` + `bg.json`
- [x] 7.7 Grep the frontend for remaining `image_url` consumers and migrate them

## 8. CSV import (optional)

- [x] 8.1 (Optional) Treat CSV `image_url` column as "create one primary image" for the product, or drop it from import

## 9. Tests

- [x] 9.1 Migration: existing image → primary row; column dropped; idempotent re-run
- [x] 9.2 Add/append: first is primary, cap at 6 → 409
- [x] 9.3 Delete: files unlinked, primary promoted; deleting last leaves no primary
- [x] 9.4 Reorder: sort_order updated, primary unchanged; set-primary flips atomically (partial unique index holds)
- [x] 9.5 Responses: `images` ordered, `primary_image_url` correct, `image_url` absent; no-images → `[]` + null
- [x] 9.6 Path-traversal guard still rejects bad product_id
- [x] 9.7 Frontend: gallery renders multiple; card uses primary; form manager uploads/reorders/deletes/sets primary

## 10. Verify

- [x] 10.1 `make test-backend`, `make test-frontend`, `make lint`
- [ ] 10.2 Manual smoke: upload 3 images → reorder → set primary → card shows primary, detail shows gallery → delete primary → next promotes
