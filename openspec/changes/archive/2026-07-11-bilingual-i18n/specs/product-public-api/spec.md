## MODIFIED Requirements

### Requirement: List products endpoint
The system SHALL expose `GET /v1/products` returning a paginated list of active products. The endpoint SHALL accept query parameters: `category` (string filter), `q` (search query), `sort` (one of: price_asc, price_desc, name, newest), `in_stock` (boolean, filter to stock > 0), `page` (integer, default 1), `limit` (integer, default 20, max 100), `locale` (one of: `en`, `bg`, default `en`). The response SHALL match the ProductListResponse schema with product name and description in the requested locale (falling back to the other language if the requested locale's content is NULL).

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

### Requirement: Get product detail endpoint
The system SHALL expose `GET /v1/products/{product_id}` returning a single active product. The endpoint SHALL accept an optional `locale` query parameter (one of: `en`, `bg`, default `en`). The response SHALL return product name and description in the requested locale with fallback to the other language. The endpoint SHALL return 404 if the product does not exist or is inactive.

#### Scenario: Get product in Bulgarian
- **WHEN** `GET /v1/products/lavender-dream-300ml?locale=bg` is called and the product has Bulgarian content
- **THEN** the response is 200 with name and description from `name_bg`/`description_bg`

#### Scenario: Get product in Bulgarian with fallback
- **WHEN** `GET /v1/products/lavender-dream-300ml?locale=bg` is called and `name_bg` is NULL
- **THEN** the response is 200 with name and description from `name_en`/`description_en` (fallback)

#### Scenario: Get product in English (default)
- **WHEN** `GET /v1/products/lavender-dream-300ml` is called without locale parameter
- **THEN** the response is 200 with English name and description
