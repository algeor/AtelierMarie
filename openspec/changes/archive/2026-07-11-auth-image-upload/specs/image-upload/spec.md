## ADDED Requirements

### Requirement: Product image upload endpoint
The system SHALL provide `POST /v1/admin/products/{product_id}/image` that accepts a multipart file upload, processes the image, and stores it as a WebP file. This endpoint requires admin authentication.

#### Scenario: Successful image upload
- **WHEN** an admin sends a valid JPEG or PNG file (≤5MB) to `POST /v1/admin/products/{product_id}/image`
- **THEN** the system:
  1. Validates the file is JPEG or PNG (by magic bytes, not just extension)
  2. Resizes to main (max 1200×1500px, aspect ratio preserved) and thumbnail (max 400×500px)
  3. Converts both to WebP format
  4. Saves to `{static_file_path}/products/{product_id}.webp` and `{product_id}_thumb.webp`
  5. Updates `products.image_url` to `/static/products/{product_id}.webp`
  6. Returns 200 with `{image_url, thumbnail_url}`

#### Scenario: Product not found
- **WHEN** an admin uploads an image for a `product_id` that does not exist in the database
- **THEN** the system returns 404 with error `"product_not_found"`

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
The system SHALL reject uploaded files larger than 5MB before attempting to process them.

#### Scenario: File within limit
- **WHEN** the uploaded file is ≤5MB (5,242,880 bytes)
- **THEN** the file is accepted for processing

#### Scenario: File exceeds limit
- **WHEN** the uploaded file is >5MB
- **THEN** the system returns 422 with error `"file_too_large"` and message indicating the 5MB limit

#### Scenario: Nginx rejects oversized upload before it reaches the app
- **WHEN** a file larger than 5MB is uploaded in production
- **THEN** Nginx (configured with `client_max_body_size 5m`) rejects the request with 413 before the body reaches FastAPI. The application-level 5MB check in image_service is a defense-in-depth fallback (handles cases where Nginx is bypassed in dev or config is misconfigured).

### Requirement: Image resize preserves aspect ratio
The system SHALL resize images using "thumbnail" mode (fit within bounding box, never upscale, preserve aspect ratio). Two sizes are produced: main (1200×1500) and thumbnail (400×500).

#### Scenario: Landscape image resized
- **WHEN** a 3000×2000px image is uploaded
- **THEN** the main image is resized to 1200×800px (width-constrained) and thumbnail to 400×267px

#### Scenario: Portrait image resized
- **WHEN** a 1000×2000px image is uploaded
- **THEN** the main image is resized to 750×1500px (height-constrained) and thumbnail to 250×500px

#### Scenario: Small image not upscaled
- **WHEN** a 300×400px image is uploaded
- **THEN** the image is NOT upscaled — saved at original dimensions (300×400) as WebP

### Requirement: WebP output format
The system SHALL save all processed images as WebP format for optimal file size and browser compatibility.

#### Scenario: WebP output with quality settings
- **WHEN** an image is processed
- **THEN** the main image is saved as WebP with quality=85 and the thumbnail with quality=80

### Requirement: Static directory created if missing
The system SHALL create the target directory `{static_file_path}/products/` if it does not exist when saving an image.

#### Scenario: Directory auto-created
- **WHEN** the products image directory does not exist on first upload
- **THEN** the system creates it (including parent directories) before saving

### Requirement: Existing image replaced on re-upload
The system SHALL overwrite existing image files when a new image is uploaded for the same product. No versioning or history is maintained. Thumbnail URL is derived by convention (`{product_id}_thumb.webp`), not stored in the database — only `products.image_url` (the main image path) is persisted.

#### Scenario: Re-upload overwrites
- **WHEN** an admin uploads a new image for a product that already has an image
- **THEN** the old `.webp` and `_thumb.webp` files are overwritten with the new processed images

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
The system SHALL strip all EXIF/metadata from uploaded images before saving. The WebP output SHALL contain no embedded metadata from the original file (prevents leaking GPS coordinates, device info, or other PII).

#### Scenario: Metadata removed
- **WHEN** an image containing EXIF data (GPS, camera model, etc.) is processed
- **THEN** the saved WebP files contain no EXIF or XMP metadata from the original
