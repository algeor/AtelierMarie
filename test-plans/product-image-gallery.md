# Product Image Gallery Test Plan

## Automated Checks

Run these before release:

```bash
uv run pytest
cd frontend && npm test
cd frontend && npm run build
```

Expected result:
- Backend tests pass, including product image service, image upload, migration, cart, and product routes.
- Frontend tests pass.
- Next.js production build passes type checking.

## Backend API Scenarios

Use an admin-authenticated client.

1. Create a product with no images.
   - Response contains `images: []`, `primary_image_url: null`, and no product-level `image_url`.

2. Upload one valid JPEG or PNG to `POST /v1/admin/products/{id}/images`.
   - Response is `201`.
   - File paths use `{product_id}_{image_id}.webp` and `{product_id}_{image_id}_thumb.webp`.
   - The image row has `sort_order = 0` and `is_primary = true`.
   - Public product detail/list responses expose the image in `images` and set `primary_image_url`.

3. Upload additional images until the product has 6.
   - Each upload appends without overwriting existing files.
   - Only the first image remains primary unless changed explicitly.
   - A seventh upload returns `409` with `max_product_images`.

4. Reorder images with `PATCH /v1/admin/products/{id}/images/reorder`.
   - `sort_order` follows the submitted `ordered_ids` list.
   - The primary image is unchanged.
   - Missing, duplicate, or foreign image IDs return `422`.

5. Set primary with `PATCH /v1/admin/products/{id}/images/{image_id}/primary`.
   - The selected image becomes the only primary.
   - The partial unique index prevents multiple primaries.

6. Delete images with `DELETE /v1/admin/products/{id}/images/{image_id}`.
   - Deleted image row is removed.
   - Main and thumbnail WebP files are unlinked when local static files exist.
   - Deleting the primary promotes the remaining lowest `sort_order` image.
   - Deleting the last image leaves `images: []` and null primary fields.

7. Validate upload hardening.
   - Non-image uploads return `422 invalid_image_type`.
   - Files over 5MB return `422 file_too_large`.
   - Bad product slugs return `400 invalid_product_id`.
   - Oversized pixel dimensions return `422 image_dimensions_too_large`.

## Migration Scenarios

Test against a copy of a database that still has `products.image_url`.

1. Start the app or run DB initialization once.
   - `product_images` exists with the product FK, `(product_id, sort_order)` index, and one-primary partial unique index.
   - Each non-empty legacy `products.image_url` becomes one primary `product_images` row.
   - Thumbnail URL follows the old `{product_id}_thumb.webp` convention.
   - `products.image_url` is removed.

2. Run initialization a second time.
   - No duplicate image rows are created.
   - Existing gallery rows remain intact.

## Frontend Admin Smoke Test

1. Open the admin product create form.
   - Create a product without images.
   - Create another product and select multiple image files.
   - Save and confirm the product detail shows the gallery.

2. Open the admin product edit form for a product with multiple images.
   - Move an image up/down and save.
   - Mark a different image as primary and save.
   - Delete the current primary and save.
   - Add more images until the cap is reached; the file input should disable at 6.

3. Confirm after each save:
   - Admin form reflects the saved order and primary image.
   - Product listing card uses the primary image.
   - Product detail shows ordered thumbnails and switches the large image when a thumbnail is selected.

## Storefront Regression Checks

1. Product cards with no images render the existing placeholder.
2. Product cards with images render `primary_image_url`.
3. Product detail with one image renders a single large image and no thumbnail strip.
4. Product detail with multiple images renders the thumbnail strip in `sort_order`.
5. Cart drawer, checkout, and order flows still render with embedded product image fields.

## CSV Import Compatibility

Import a CSV containing `image_url`.

- The product is created or updated normally.
- The URL is appended as a gallery image instead of being stored on `products`.
- If the product had no images, the imported URL becomes primary.
- If the product already has images, the imported URL appends until the six-image cap.
