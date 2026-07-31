## MODIFIED Requirements

### Requirement: EXIF metadata stripped
The system SHALL apply the source image's EXIF orientation to the pixels (uprighting the image) **before** any resizing, and SHALL strip all EXIF/metadata from the saved output. The WebP output SHALL contain no embedded metadata from the original file (prevents leaking GPS coordinates, device info, or other PII) **and** SHALL be visually upright regardless of the camera/phone orientation flag on the original.

#### Scenario: Metadata removed
- **WHEN** an image containing EXIF data (GPS, camera model, etc.) is processed
- **THEN** the saved WebP files contain no EXIF or XMP metadata from the original

#### Scenario: Orientation applied so portrait photos are upright
- **WHEN** a photo whose EXIF orientation flag indicates rotation (e.g. a portrait phone photo stored as landscape-plus-flag) is processed
- **THEN** the saved WebP derivatives are rotated to their upright orientation before resizing, so they display the correct way up even though the EXIF flag itself is stripped

### Requirement: WebP output format
The system SHALL save all processed images as WebP format for optimal file size and browser compatibility.

#### Scenario: WebP output with quality settings
- **WHEN** an image is processed
- **THEN** the thumbnail is saved as WebP with quality=80, the main with quality=92, and the zoom with quality=95

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
