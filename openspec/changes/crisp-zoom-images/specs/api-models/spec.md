## MODIFIED Requirements

### Requirement: Product response model defines the product shape
The system SHALL expose product data through a `ProductResponse` schema containing: id (str), name (str), description (str|None), price_cents (int), category (str|None), `images` (list of image objects, each with id, image_url, thumbnail_url, `zoom_url`, sort_order, is_primary), `primary_image_url` (str|None), `primary_thumbnail_url` (str|None), stock (int), is_active (bool), is_featured (bool), created_at (str), updated_at (str). The former single `image_url` field is removed.

#### Scenario: Product with images serialized
- **WHEN** a product with one or more images is serialized
- **THEN** the response contains all defined fields with correct types, `images` is an ordered array where each image object includes `zoom_url`, and `primary_image_url` matches the image with `is_primary = 1`

#### Scenario: Product with no images
- **WHEN** a product with no images is serialized
- **THEN** `images` is `[]` and `primary_image_url` / `primary_thumbnail_url` are `null` (not omitted)

#### Scenario: Image object carries all three derivative URLs
- **WHEN** an image object is serialized
- **THEN** it includes `thumbnail_url`, `image_url` (main), and `zoom_url` (high-resolution), each a `/static/products/…` path
