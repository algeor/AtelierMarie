## MODIFIED Requirements

### Requirement: Product image upload endpoint
The system SHALL provide `POST /v1/admin/products/{product_id}/images` that accepts a multipart file upload, processes the image, and stores it as a new WebP image belonging to the product (appended, not overwriting existing images). This endpoint requires admin authentication.

#### Scenario: Successful image upload
- **WHEN** an admin sends a valid JPEG or PNG file (≤5MB) to `POST /v1/admin/products/{product_id}/images`
- **THEN** the system:
  1. Validates the file is JPEG or PNG (by magic bytes, not just extension)
  2. Resizes to main (max 1200×1500px, aspect ratio preserved) and thumbnail (max 400×500px)
  3. Converts both to WebP format
  4. Saves to `{static_file_path}/products/{product_id}_{image_id}.webp` and `{product_id}_{image_id}_thumb.webp`
  5. Inserts a `product_images` row (image_url, thumbnail_url, sort_order, is_primary)
  6. Returns 201 with the created image `{id, image_url, thumbnail_url, sort_order, is_primary}`

#### Scenario: Product not found
- **WHEN** an admin uploads an image for a `product_id` that does not exist in the database
- **THEN** the system returns 404 with error `"product_not_found"`

#### Scenario: Image cap reached
- **WHEN** an admin uploads an image to a product that already has 6 images
- **THEN** the system returns 409 and stores nothing

#### Scenario: Non-admin rejected
- **WHEN** a non-admin user attempts to upload a product image
- **THEN** the system returns 403 Forbidden

### Requirement: Existing image replaced on re-upload
The system SHALL store each uploaded image as a distinct file; uploads append rather than overwrite. Both `image_url` and `thumbnail_url` are persisted per image in `product_images`. Removing an image is done explicitly via the delete endpoint, which unlinks both the main and thumbnail WebP files.

#### Scenario: Uploads do not overwrite
- **WHEN** an admin uploads a second image for a product that already has one
- **THEN** both images exist as separate files and separate `product_images` rows

#### Scenario: Delete removes both files
- **WHEN** an admin deletes an image
- **THEN** its `.webp` and `_thumb.webp` files are unlinked and its row removed
