## Purpose

Defines product image upload, processing, validation, storage, and image safety behavior.
## Requirements
### Requirement: Product image upload endpoint
The system SHALL provide `POST /v1/admin/products/{product_id}/images` that accepts a multipart file upload, processes the image, and stores it as a new WebP image belonging to the product (appended, not overwriting existing images). This endpoint requires admin authentication.

#### Scenario: Successful image upload
- **WHEN** an admin sends a valid JPEG or PNG file (≤25MB) to `POST /v1/admin/products/{product_id}/images`
- **THEN** the system:
  1. Validates the file is JPEG or PNG (by magic bytes, not just extension)
  2. Resizes to main (max 2000×2500px, aspect ratio preserved) and thumbnail (max 400×500px)
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

### Requirement: File type validation
The system SHALL reject files that are not JPEG or PNG. Validation is by file magic bytes (header inspection), not by Content-Type header or file extension alone.

#### Scenario: Valid JPEG accepted
- **WHEN** the uploaded file starts with JPEG magic bytes (`FF D8 FF`)
- **THEN** the file is accepted for processing

#### Scenario: Valid PNG accepted
- **WHEN** the uploaded file starts with PNG magic bytes (`89 50 4E 47`)
- **THEN** the file is accepted for processing

#### Scenario: Invalid file type rejected
- **WHEN** the uploaded file does not match JPEG or PNG magic bytes (e.g., a GIF, SVG, or renamed text file)
- **THEN** the system returns 422 with error `"invalid_image_type"` and message indicating only JPEG/PNG are accepted

### Requirement: File size limit
The system SHALL reject uploaded files larger than 25MB before attempting to process them.

#### Scenario: File within limit
- **WHEN** the uploaded file is ≤25MB (26,214,400 bytes)
- **THEN** the file is accepted for processing

#### Scenario: File exceeds limit
- **WHEN** the uploaded file is >25MB
- **THEN** the system returns 422 with error `"file_too_large"` and message indicating the 25MB limit

#### Scenario: Streaming chunk guard rejects oversized upload mid-stream
- **WHEN** an upload's accumulated bytes exceed 25MB during streaming read in the admin route
- **THEN** the route stops reading and returns 422 `"file_too_large"` before buffering the whole body

#### Scenario: Nginx allows exact-limit multipart uploads and caps truly oversized bodies
- **WHEN** an exact 25MB file is uploaded in production as multipart form data
- **THEN** Nginx does not reject it solely because of multipart overhead because `client_max_body_size` is configured to `27m`
- **AND** the application-level 25MB checks in image_service and the admin route remain the source of truth for file-byte validation

#### Scenario: Nginx rejects bodies above the proxy cap
- **WHEN** an upload request body exceeds `client_max_body_size 27m`
- **THEN** Nginx rejects the request with 413 before the body reaches FastAPI.

### Requirement: Image resize preserves aspect ratio
The system SHALL resize images using "thumbnail" mode (fit within bounding box, never upscale, preserve aspect ratio). Three sizes are produced: thumbnail (400×500), main (2000×2500), and zoom (3000×3750).

#### Scenario: Landscape image resized
- **WHEN** a 6000×4000px image is uploaded
- **THEN** the zoom image is width-constrained to 3000×2000px, the main to 2000×1333px, and the thumbnail to 400×267px

#### Scenario: Portrait image resized
- **WHEN** a 4000×6000px image is uploaded
- **THEN** the zoom image is height-constrained to 2500×3750px, the main to 1667×2500px, and the thumbnail to 333×500px

#### Scenario: Small image not upscaled
- **WHEN** a 300×400px image is uploaded
- **THEN** none of the derivatives are upscaled — each is saved at the original 300×400 dimensions as WebP

#### Scenario: Zoom dimensions stay under the pixel-flood ceiling
- **WHEN** the zoom bounding box (3000×3750 = 11.25 megapixels) is applied
- **THEN** it remains below the `MAX_IMAGE_PIXELS` 25-megapixel safety ceiling, which is left unchanged

### Requirement: WebP output format
The system SHALL save all processed images as WebP format for optimal file size and browser compatibility.

#### Scenario: WebP output with quality settings
- **WHEN** an image is processed
- **THEN** the thumbnail is saved as WebP with quality=80, the main with quality=92, and the zoom with quality=95

### Requirement: Static directory created if missing
The system SHALL create the target directory `{static_file_path}/products/` if it does not exist when saving an image.

#### Scenario: Directory auto-created
- **WHEN** the products image directory does not exist on first upload
- **THEN** the system creates it (including parent directories) before saving

### Requirement: Existing image replaced on re-upload
The system SHALL store each uploaded image as a distinct file; uploads append rather than overwrite. Both `image_url` and `thumbnail_url` are persisted per image in `product_images`. Removing an image is done explicitly via the delete endpoint, which unlinks both the main and thumbnail WebP files.

#### Scenario: Uploads do not overwrite
- **WHEN** an admin uploads a second image for a product that already has one
- **THEN** both images exist as separate files and separate `product_images` rows

#### Scenario: Delete removes both files
- **WHEN** an admin deletes an image
- **THEN** its `.webp` and `_thumb.webp` files are unlinked and its row removed

### Requirement: Path traversal prevention
The system SHALL validate that the `product_id` used in file path construction does not contain path traversal sequences. The resolved output path MUST be within `{static_file_path}/products/`.

#### Scenario: Path traversal in product_id rejected
- **WHEN** the image service constructs a file path from `product_id`
- **THEN** the system SHALL verify the resolved path (via `pathlib.Path.resolve()`) is under `{static_file_path}/products/`, and reject with 400 if not

#### Scenario: Slash and dot-dot in product_id
- **WHEN** a `product_id` contains `/`, `\`, `..`, or null bytes
- **THEN** the system SHALL reject the request (note: product creation should already prevent this, but image upload verifies defensively)

#### Scenario: Product_id format validated via allowlist
- **WHEN** the image service receives a `product_id` for path construction
- **THEN** it SHALL validate the `product_id` matches the slug format (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`) BEFORE constructing any file path. This allowlist approach is more robust than blocklisting traversal characters and aligns with the project convention that product IDs are slugs like `lavender-dream-300ml`.

### Requirement: Pixel flood protection
The system SHALL reject images with excessively large pixel dimensions to prevent decompression bombs that could cause OOM.

#### Scenario: Image within pixel limit
- **WHEN** an uploaded image has dimensions resulting in ≤25 million total pixels (e.g., 5000×5000)
- **THEN** the image is accepted for processing

#### Scenario: Pixel flood rejected
- **WHEN** an uploaded image has dimensions exceeding 25 million total pixels (e.g., 64000×64000)
- **THEN** the system returns 422 with error `"image_dimensions_too_large"` (set `PIL.Image.MAX_IMAGE_PIXELS = 25_000_000`)

### Requirement: EXIF metadata stripped
The system SHALL apply the source image's EXIF orientation to the pixels (uprighting the image) **before** any resizing, and SHALL strip all EXIF/metadata from the saved output. The WebP output SHALL contain no embedded metadata from the original file (prevents leaking GPS coordinates, device info, or other PII) **and** SHALL be visually upright regardless of the camera/phone orientation flag on the original.

#### Scenario: Metadata removed
- **WHEN** an image containing EXIF data (GPS, camera model, etc.) is processed
- **THEN** the saved WebP files contain no EXIF or XMP metadata from the original

#### Scenario: Orientation applied so portrait photos are upright
- **WHEN** a photo whose EXIF orientation flag indicates rotation (e.g. a portrait phone photo stored as landscape-plus-flag) is processed
- **THEN** the saved WebP derivatives are rotated to their upright orientation before resizing, so they display the correct way up even though the EXIF flag itself is stripped

### Requirement: High-resolution zoom derivative
The system SHALL produce a high-resolution "zoom" WebP derivative (max bounding box 3000×3750, quality 95) for every uploaded product image, in addition to the main and thumbnail derivatives. The zoom derivative SHALL be a downscaled, EXIF-stripped re-encode — never the byte-for-byte uploaded original. The processing result SHALL include a `zoom_url` (`/static/products/{stem}_zoom.webp`).

#### Scenario: Zoom derivative generated on upload
- **WHEN** an image is successfully processed
- **THEN** a `{stem}_zoom.webp` file is written under `static/products/` and the result includes a `zoom_url` pointing to it

#### Scenario: Zoom derivative path is traversal-safe
- **WHEN** the zoom output path is resolved
- **THEN** it is verified to be under the products base directory (same guard as main/thumbnail); a path escaping the base directory raises a processing error

#### Scenario: Zoom respects the pixel ceiling
- **WHEN** any image is processed
- **THEN** the 25-megapixel decompression-bomb cap (`MAX_IMAGE_PIXELS`) still applies unchanged; a source exceeding 25MP is rejected regardless of the 25MB byte limit

