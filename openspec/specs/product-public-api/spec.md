## Purpose

Defines public product API behavior and response contracts used by storefront listing and detail views.

## Requirements
### Requirement: List products endpoint
The system SHALL expose `GET /v1/products` returning a paginated list of active products. The endpoint SHALL accept query parameters: `category` (string filter), `q` (search query), `sort` (one of: price_asc, price_desc, name, newest), `in_stock` (boolean, filter to stock > 0), `page` (integer, default 1), `limit` (integer, default 20, max 100), `locale` (one of: `en`, `bg`, default `en`). The response SHALL match the ProductListResponse schema with product name and description in the requested locale (falling back to the other language if the requested locale's content is NULL). The list operation SHALL capture `now` once and use it for all effective-price calculations and price sorting in the response. Each product SHALL include `price_cents` (original list price), `effective_price_cents` (discounted price, equal to `price_cents` when no discount is active), `discount_percent` (active display percent or null), and `discount_active` (boolean). Public product responses SHALL NOT expose `discount_starts_at` or `discount_ends_at`.

For `sort=price_asc` and `sort=price_desc`, products SHALL be ordered by `effective_price_cents` at request time before pagination. Search results without an explicit sort keep relevance order; search results with an explicit price sort use the same effective-price ordering.

#### Scenario: List all products with defaults
- **WHEN** `GET /v1/products` is called with no parameters
- **THEN** the response is 200 with `{products: [...], total: N, page: 1, limit: 20}` containing only active products with English content

#### Scenario: List products in Bulgarian
- **WHEN** `GET /v1/products?locale=bg` is called
- **THEN** products are returned with Bulgarian name and description (falling back to English if BG is NULL)

#### Scenario: Search uses locale-appropriate FTS index
- **WHEN** `GET /v1/products?q=лавандула&locale=bg` is called
- **THEN** the system searches the Bulgarian FTS index and returns matching products with BG content

#### Scenario: Search in English (default)
- **WHEN** `GET /v1/products?q=lavender` is called without locale parameter
- **THEN** the system searches the English FTS index and returns matching products with EN content

#### Scenario: Discounted product exposes effective price
- **WHEN** a listed product has an active 20% discount and `price_cents` = 3250
- **THEN** its entry includes `price_cents` = 3250, `effective_price_cents` = 2600, `discount_percent` = 20, `discount_active` = true

#### Scenario: Future scheduled discount is hidden publicly
- **WHEN** a listed product has `discount_percent` = 20 but its start time is in the future
- **THEN** its entry includes `effective_price_cents` equal to `price_cents`, `discount_percent` = null, and `discount_active` = false

#### Scenario: Price sort uses effective price
- **WHEN** product A has `price_cents` = 4000 with an active 50% discount and product B has `price_cents` = 3000 with no discount
- **THEN** `GET /v1/products?sort=price_asc` returns product A before product B because 2000 < 3000

### Requirement: Get product detail endpoint
The system SHALL expose `GET /v1/products/{product_id}` returning a single active product. The endpoint SHALL accept an optional `locale` query parameter (one of: `en`, `bg`, default `en`). The response SHALL return product name and description in the requested locale with fallback to the other language. The response SHALL include `price_cents`, `effective_price_cents`, public `discount_percent` (active display percent or null), and `discount_active`; it SHALL NOT expose discount window timestamps. The endpoint SHALL return 404 if the product does not exist or is inactive.

#### Scenario: Get product in Bulgarian
- **WHEN** `GET /v1/products/lavender-dream-300ml?locale=bg` is called and the product has Bulgarian content
- **THEN** the response is 200 with name and description from `name_bg`/`description_bg`

#### Scenario: Get product in Bulgarian with fallback
- **WHEN** `GET /v1/products/lavender-dream-300ml?locale=bg` is called and `name_bg` is NULL
- **THEN** the response is 200 with name and description from `name_en`/`description_en` (fallback)

#### Scenario: Get product in English (default)
- **WHEN** `GET /v1/products/lavender-dream-300ml` is called without locale parameter
- **THEN** the response is 200 with English name and description

#### Scenario: Detail response includes discount fields
- **WHEN** a product with no active discount is fetched
- **THEN** the response includes `effective_price_cents` equal to `price_cents`, `discount_percent` = null, `discount_active` = false

### Requirement: Public product responses expose the image gallery
Public product list and detail responses SHALL include the ordered `images` array and the computed `primary_image_url` / `primary_thumbnail_url` fields, and SHALL NOT include the removed `image_url` field.

#### Scenario: Detail response includes images
- **WHEN** `GET /v1/products/{id}` is called for a product with 3 images
- **THEN** the response includes an ordered `images` array of 3 entries and `primary_image_url` equal to the primary image's URL

#### Scenario: List response includes primary image
- **WHEN** `GET /v1/products` is called
- **THEN** each product includes `primary_image_url` (or `null` when it has no images)

### Requirement: Public product responses include safety metadata
Public product list and detail responses SHALL include localized safety warning and care instruction fields needed by the storefront. The fields SHALL resolve according to the requested locale with fallback behavior consistent with product name/description localization.

#### Scenario: Detail response includes localized safety metadata
- **WHEN** `GET /v1/products/{id}?locale=bg` is called for a product with Bulgarian safety metadata
- **THEN** the response includes Bulgarian safety warnings and care instructions

#### Scenario: Safety metadata falls back to English
- **WHEN** `GET /v1/products/{id}?locale=bg` is called and Bulgarian safety metadata is empty
- **THEN** the response falls back to English safety metadata when available

#### Scenario: List response includes safety metadata without admin-only fields
- **WHEN** `GET /v1/products` is called
- **THEN** each public product may include resolved safety metadata
- **AND** the response does not expose admin-only translation staleness fields
