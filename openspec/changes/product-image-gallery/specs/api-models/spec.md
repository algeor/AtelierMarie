## MODIFIED Requirements

### Requirement: Product response model defines the product shape
The system SHALL expose product data through a `ProductResponse` schema containing: id (str), name (str), description (str|None), price_cents (int), category (str|None), `images` (list of image objects, each with id, image_url, thumbnail_url, sort_order, is_primary), `primary_image_url` (str|None), `primary_thumbnail_url` (str|None), stock (int), is_active (bool), is_featured (bool), created_at (str), updated_at (str). The former single `image_url` field is removed.

#### Scenario: All fields present
- **WHEN** a product is serialized to JSON
- **THEN** the response contains all defined fields with correct types, `images` is an ordered array, and `primary_image_url` matches the image with `is_primary = 1`

#### Scenario: Product with no images
- **WHEN** a product has no images
- **THEN** `images` is `[]` and `primary_image_url` / `primary_thumbnail_url` are `null` (not omitted)

#### Scenario: Nullable fields
- **WHEN** a product has no description or category
- **THEN** those fields are `null` in the response (not omitted)

### Requirement: Product list response includes pagination
The system SHALL wrap product lists in a `ProductListResponse` containing: products (list[ProductResponse]), total (int), page (int), limit (int).

#### Scenario: Paginated product listing
- **WHEN** a client requests products with page=2, limit=10
- **THEN** the response contains at most 10 products, total reflects the full count, and page=2
