## MODIFIED Requirements

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

#### Scenario: Nginx rejects oversized upload before it reaches the app
- **WHEN** a file larger than 25MB is uploaded in production
- **THEN** Nginx (configured with `client_max_body_size 25m`) rejects the request with 413 before the body reaches FastAPI. The application-level 25MB checks in image_service and the admin route are defense-in-depth fallbacks.

### Requirement: Image resize preserves aspect ratio
The system SHALL resize images using "thumbnail" mode (fit within bounding box, never upscale, preserve aspect ratio). Three sizes are produced: thumbnail (400×500), main (2000×2500), and zoom (2400×3000).

#### Scenario: Landscape image resized
- **WHEN** a 6000×4000px image is uploaded
- **THEN** the zoom image is width-constrained to 2400×1600px, the main to 2000×1333px, and the thumbnail to 400×267px

#### Scenario: Portrait image resized
- **WHEN** a 3000×6000px image is uploaded
- **THEN** the zoom image is height-constrained to 1500×3000px, the main to 1250×2500px, and the thumbnail to 250×500px

#### Scenario: Small image not upscaled
- **WHEN** a 300×400px image is uploaded
- **THEN** none of the derivatives are upscaled — each is saved at the original 300×400 dimensions as WebP

### Requirement: WebP output format
The system SHALL save all processed images as WebP format for optimal file size and browser compatibility.

#### Scenario: WebP output with quality settings
- **WHEN** an image is processed
- **THEN** the thumbnail is saved as WebP with quality=80, the main with quality=88, and the zoom with quality=90

## ADDED Requirements

### Requirement: High-resolution zoom derivative
The system SHALL produce a high-resolution "zoom" WebP derivative (max bounding box 2400×3000, quality 90) for every uploaded product image, in addition to the main and thumbnail derivatives. The zoom derivative SHALL be a downscaled, EXIF-stripped re-encode — never the byte-for-byte uploaded original. The processing result SHALL include a `zoom_url` (`/static/products/{stem}_zoom.webp`).

#### Scenario: Zoom derivative generated on upload
- **WHEN** an image is successfully processed
- **THEN** a `{stem}_zoom.webp` file is written under `static/products/` and the result includes a `zoom_url` pointing to it

#### Scenario: Zoom derivative path is traversal-safe
- **WHEN** the zoom output path is resolved
- **THEN** it is verified to be under the products base directory (same guard as main/thumbnail); a path escaping the base directory raises a processing error

#### Scenario: Zoom respects the pixel ceiling
- **WHEN** any image is processed
- **THEN** the 25-megapixel decompression-bomb cap (`MAX_IMAGE_PIXELS`) still applies unchanged; a source exceeding 25MP is rejected regardless of the 25MB byte limit
