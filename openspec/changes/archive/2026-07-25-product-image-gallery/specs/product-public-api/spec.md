## ADDED Requirements

### Requirement: Public product responses expose the image gallery
Public product list and detail responses SHALL include the ordered `images` array and the computed `primary_image_url` / `primary_thumbnail_url` fields, and SHALL NOT include the removed `image_url` field.

#### Scenario: Detail response includes images
- **WHEN** `GET /v1/products/{id}` is called for a product with 3 images
- **THEN** the response includes an ordered `images` array of 3 entries and `primary_image_url` equal to the primary image's URL

#### Scenario: List response includes primary image
- **WHEN** `GET /v1/products` is called
- **THEN** each product includes `primary_image_url` (or `null` when it has no images)
