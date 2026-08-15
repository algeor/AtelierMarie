## MODIFIED Requirements

### Requirement: Product image upload endpoint
The system SHALL provide `POST /v1/admin/products/{product_id}/images` that accepts a multipart file upload, processes the image, and stores it as a new WebP image belonging to the product (appended, not overwriting existing images). This endpoint requires admin authentication.

#### Scenario: Successful image upload
- **WHEN** an admin sends a valid JPEG or PNG file (≤25MB) to `POST /v1/admin/products/{product_id}/images`
- **THEN** the system:
  1. Validates the file is JPEG or PNG (by magic bytes, not just extension)
  2. Resizes to main (max 2000×2500px, aspect ratio preserved) and thumbnail (max 400×500px)
  3. Converts both to WebP format
  4. Uploads the variants to R2 under keys `products/{product_id}_{image_id}.webp` and `products/{product_id}_{image_id}_thumb.webp`
  5. Inserts a `product_images` row (image_url, thumbnail_url, sort_order, is_primary) with the R2 public URLs
  6. Returns 201 with the created image `{id, image_url, thumbnail_url, sort_order, is_primary}` where the URLs are absolute R2 public URLs

#### Scenario: Product not found
- **WHEN** an admin uploads an image for a `product_id` that does not exist in the database
- **THEN** the system returns 404 with error `"product_not_found"`

#### Scenario: Image cap reached
- **WHEN** an admin uploads an image to a product that already has 6 images
- **THEN** the system returns 409 and stores nothing

#### Scenario: Non-admin rejected
- **WHEN** a non-admin user attempts to upload a product image
- **THEN** the system returns 403 Forbidden

### Requirement: WebP output format
The system SHALL save all processed images as WebP format for optimal file size and browser compatibility. Each variant SHALL be uploaded to R2 with `ContentType: image/webp`.

#### Scenario: WebP output with quality settings
- **WHEN** an image is processed
- **THEN** the thumbnail is encoded as WebP with quality=80, the main with quality=92, and the zoom with quality=95, and each is uploaded with content type `image/webp`

### Requirement: Existing image replaced on re-upload
The system SHALL store each uploaded image as a distinct object; uploads append rather than overwrite. Both `image_url` and `thumbnail_url` (plus `zoom_url`) are persisted per image in `product_images` as R2 public URLs. Removing an image is done explicitly via the delete endpoint, which deletes the main, thumbnail, and zoom objects from R2.

#### Scenario: Uploads do not overwrite
- **WHEN** an admin uploads a second image for a product that already has one
- **THEN** both images exist as separate R2 objects and separate `product_images` rows

#### Scenario: Delete removes all variants
- **WHEN** an admin deletes an image
- **THEN** its main, `_thumb`, and `_zoom` WebP objects are deleted from R2 and its row removed

### Requirement: Path traversal prevention
The system SHALL validate that the `product_id` used in object-key construction does not contain path traversal sequences. The derived object key MUST remain under the `products/` prefix.

#### Scenario: Path traversal in product_id rejected
- **WHEN** the image service constructs an object key from `product_id`
- **THEN** the system SHALL verify the derived key stays under the `products/` prefix and reject with 400 if not

#### Scenario: Slash and dot-dot in product_id
- **WHEN** a `product_id` contains `/`, `\`, `..`, or null bytes
- **THEN** the system SHALL reject the request (note: product creation should already prevent this, but image upload verifies defensively)

#### Scenario: Product_id format validated via allowlist
- **WHEN** the image service receives a `product_id` for key construction
- **THEN** it SHALL validate the `product_id` matches the slug format (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`) BEFORE constructing any object key. This allowlist approach is more robust than blocklisting traversal characters and aligns with the project convention that product IDs are slugs like `lavender-dream-300ml`.

### Requirement: High-resolution zoom derivative
The system SHALL produce a high-resolution "zoom" WebP derivative (max bounding box 3000×3750, quality 95) for every uploaded product image, in addition to the main and thumbnail derivatives. The zoom derivative SHALL be a downscaled, EXIF-stripped re-encode — never the byte-for-byte uploaded original. The processing result SHALL include a `zoom_url` that is the R2 public URL of the object at key `products/{stem}_zoom.webp`.

#### Scenario: Zoom derivative generated on upload
- **WHEN** an image is successfully processed
- **THEN** a `products/{stem}_zoom.webp` object is uploaded to R2 and the result includes a `zoom_url` pointing to its R2 public URL

#### Scenario: Zoom derivative key is traversal-safe
- **WHEN** the zoom object key is derived
- **THEN** it is verified to stay under the `products/` prefix (same guard as main/thumbnail); a key escaping the prefix raises a processing error

#### Scenario: Zoom respects the pixel ceiling
- **WHEN** any image is processed
- **THEN** the 25-megapixel decompression-bomb cap (`MAX_IMAGE_PIXELS`) still applies unchanged; a source exceeding 25MP is rejected regardless of the 25MB byte limit

## REMOVED Requirements

### Requirement: Static directory created if missing
**Reason**: Product media is no longer written to the local `{static_file_path}/products/` directory; images are uploaded to the R2 bucket, which requires no per-request directory creation. The `/static` mount is retired for product media.
**Migration**: Ensure the R2 bucket exists and R2 credentials are configured (`r2_bucket`, `r2_endpoint_url`, `r2_access_key_id`, `r2_secret_access_key`, `r2_public_base_url`). Existing on-disk files are migrated by the one-time backfill script defined in the `object-media-storage` capability.
