## Purpose

Defines product image gallery ordering, primary image behavior, storefront rendering, and gallery management contracts.
## Requirements
### Requirement: Products support multiple images
The system SHALL persist product images in a `product_images` table (id, product_id, image_url, thumbnail_url, sort_order, is_primary, created_at), supporting up to 6 images per product. Images SHALL belong to a product and have a stable display order via `sort_order`.

#### Scenario: Append images up to the cap
- **WHEN** an admin uploads a 1st through 6th image to a product
- **THEN** each is stored as a `product_images` row for that product

#### Scenario: Cap enforced at 6
- **WHEN** an admin uploads a 7th image to a product that already has 6
- **THEN** the request is rejected with 409 and no image is stored

#### Scenario: Images processed with unique filenames
- **WHEN** an image is uploaded
- **THEN** it is validated, resized, EXIF-stripped, and stored as WebP at `{product_id}_{image_id}.webp` (+ `_thumb`), never overwriting another image

### Requirement: Exactly one primary image per product
A product with at least one image SHALL have exactly one image with `is_primary = 1`; a product with no images SHALL have no primary. The first image uploaded to a product SHALL become primary. The database SHALL enforce at most one primary per product via a partial unique index.

#### Scenario: First image becomes primary
- **WHEN** the first image is added to a product
- **THEN** that image has `is_primary = 1`

#### Scenario: Subsequent images are not primary
- **WHEN** a second image is added
- **THEN** it has `is_primary = 0` and the existing primary is unchanged

#### Scenario: Set a different primary
- **WHEN** an admin sets image B as primary while image A was primary
- **THEN** image B becomes `is_primary = 1` and image A becomes `is_primary = 0`, atomically

#### Scenario: Deleting the primary promotes another
- **WHEN** the primary image is deleted and other images remain
- **THEN** the remaining image with the lowest `sort_order` becomes primary

#### Scenario: Deleting the last image leaves no primary
- **WHEN** the only image of a product is deleted
- **THEN** the product has no images and no primary

### Requirement: Image management endpoints
The system SHALL provide admin-authenticated endpoints to append, delete, reorder, and set the primary of a product's images. All SHALL require admin auth and validate the product exists.

#### Scenario: Append image
- **WHEN** an admin `POST`s a valid image to `/v1/admin/products/{id}/images`
- **THEN** the image is processed and returned, becoming primary if it is the product's first

#### Scenario: Delete image
- **WHEN** an admin `DELETE`s `/v1/admin/products/{id}/images/{image_id}`
- **THEN** the row and its WebP files are removed, and primary is promoted if needed

#### Scenario: Reorder images
- **WHEN** an admin `PATCH`es `/v1/admin/products/{id}/images/reorder` with an ordered list of image ids
- **THEN** each image's `sort_order` is updated to match, without changing which image is primary

#### Scenario: Set primary
- **WHEN** an admin `PATCH`es `/v1/admin/products/{id}/images/{image_id}/primary`
- **THEN** that image becomes the sole primary for the product

#### Scenario: Non-admin rejected
- **WHEN** a non-admin calls any image-management endpoint
- **THEN** the request is rejected with 401/403

### Requirement: Migration from single image_url to image gallery
The system SHALL migrate existing single-image data into `product_images` and remove the `products.image_url` column. The migration SHALL be idempotent.

#### Scenario: Existing image becomes primary row
- **WHEN** migration runs for a product that had `image_url` set
- **THEN** a `product_images` row is created with that URL, `is_primary = 1`, `sort_order = 0`

#### Scenario: image_url column removed
- **WHEN** migration completes
- **THEN** `products` no longer has an `image_url` column and product reads assemble images from `product_images`

#### Scenario: Migration runs once
- **WHEN** the app restarts after migration
- **THEN** no duplicate image rows are created

### Requirement: Retina-crisp gallery hero
The product gallery hero SHALL render the main (`image_url`) derivative, which is sized large enough (max 2000×2500) to appear crisp on high-density (2×) displays at the gallery's on-page layout size without browser upscaling.

#### Scenario: Hero renders the main derivative
- **WHEN** the product detail page renders a product with images
- **THEN** the hero image `src` resolves to the selected image's `image_url` (main) derivative

### Requirement: Click-to-zoom lightbox
The product gallery SHALL provide a single, unified media lightbox that displays **all** of the product's media — every image and the video (if present) — as an ordered, navigable carousel following the gallery's existing display order (`sort_order`, primary image first). Activating any gallery item (hero or thumbnail) SHALL open the lightbox positioned on that item.

Within the lightbox:
- **Image slides** SHALL support pan and pinch/scroll zoom into detail, sourced from the high-resolution `zoom_url` derivative, falling back to `image_url` when `zoom_url` is null or absent. The zoom asset SHALL be loaded lazily — only when its slide is shown, not on initial product page load.
- The lightbox SHALL allow navigation across the entire media set (next/previous via arrow keys and swipe, and direct selection via thumbnails), so the user can move photo → video → photo without leaving the viewer.
- The lightbox SHALL be keyboard accessible: it exposes a dialog role, traps focus, and closes on Escape or backdrop interaction.

#### Scenario: Open unified media lightbox
- **WHEN** the customer activates a gallery item (hero or a thumbnail)
- **THEN** the lightbox opens positioned on that item, containing all of the product's images and video as ordered slides

#### Scenario: Pan and pinch-zoom into image detail
- **WHEN** an image slide is shown and the customer zooms in
- **THEN** the slide renders the `zoom_url` derivative and the customer can pan around the enlarged image to inspect fine detail

#### Scenario: Navigate across images and video in one flow
- **WHEN** the lightbox is open on an image slide adjacent to the video slide
- **THEN** advancing (arrow/swipe/thumbnail) moves to the video slide, and continuing advances to the next image — all within the same lightbox

#### Scenario: Zoom asset loaded lazily
- **WHEN** the product detail page first loads
- **THEN** no `zoom_url` asset is requested until its slide is displayed in the lightbox

#### Scenario: Zoom fallback when no zoom asset
- **WHEN** an image slide's `zoom_url` is null or absent
- **THEN** the slide falls back to rendering `image_url` rather than failing

#### Scenario: Lightbox is keyboard accessible
- **WHEN** the lightbox is open
- **THEN** it exposes a dialog role, traps focus, and closes on Escape or backdrop interaction

