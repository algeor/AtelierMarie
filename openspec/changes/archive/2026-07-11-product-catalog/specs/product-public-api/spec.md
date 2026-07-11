## ADDED Requirements

### Requirement: List products endpoint
The system SHALL expose `GET /v1/products` returning a paginated list of active products. The endpoint SHALL accept query parameters: `category` (string filter), `q` (search query), `sort` (one of: price_asc, price_desc, name, newest), `in_stock` (boolean, filter to stock > 0), `page` (integer, default 1), `limit` (integer, default 20, max 100). The response SHALL match the ProductListResponse schema.

#### Scenario: List all products with defaults
- **WHEN** `GET /v1/products` is called with no parameters
- **THEN** the response is 200 with `{products: [...], total: N, page: 1, limit: 20}` containing only active products

#### Scenario: Filter by category
- **WHEN** `GET /v1/products?category=dessert` is called
- **THEN** only active products with category "dessert" are returned

#### Scenario: Search by query string
- **WHEN** `GET /v1/products?q=lavender` is called
- **THEN** active products matching "lavender" in name or description are returned, sorted by relevance

#### Scenario: Sort by price ascending
- **WHEN** `GET /v1/products?sort=price_asc` is called
- **THEN** products are returned sorted by price_cents ascending

#### Scenario: Filter in-stock only
- **WHEN** `GET /v1/products?in_stock=true` is called
- **THEN** only products with stock > 0 are returned

#### Scenario: Pagination boundary
- **WHEN** `GET /v1/products?page=999` is called and not enough products exist
- **THEN** the response is 200 with an empty products list and the correct total

#### Scenario: Limit capped at 100
- **WHEN** `GET /v1/products?limit=500` is called
- **THEN** the limit is capped to 100 in the response

#### Scenario: Search with explicit sort overrides relevance
- **WHEN** `GET /v1/products?q=lavender&sort=price_asc` is called
- **THEN** products matching "lavender" are returned sorted by price ascending (sort overrides FTS5 relevance ranking)

#### Scenario: Search without sort uses relevance
- **WHEN** `GET /v1/products?q=lavender` is called without a `sort` parameter
- **THEN** products are returned sorted by FTS5 relevance ranking (best match first)

### Requirement: Get product detail endpoint
The system SHALL expose `GET /v1/products/{product_id}` returning a single active product. The endpoint SHALL return 404 if the product does not exist or is inactive.

#### Scenario: Get existing active product
- **WHEN** `GET /v1/products/lavender-dream-300ml` is called and the product is active
- **THEN** the response is 200 with the full ProductResponse

#### Scenario: Get inactive product
- **WHEN** `GET /v1/products/discontinued-candle` is called and the product is inactive
- **THEN** the response is 404 with error body `{error: {code: "NOT_FOUND", message: "Product not found"}}`

#### Scenario: Get non-existent product
- **WHEN** `GET /v1/products/no-such-id` is called
- **THEN** the response is 404

### Requirement: Public endpoints require no authentication
The `GET /v1/products` and `GET /v1/products/{id}` endpoints SHALL be accessible without any authentication. No session cookie, JWT, or API key is required.

#### Scenario: Anonymous access succeeds
- **WHEN** `GET /v1/products` is called without any auth headers or cookies
- **THEN** the response is 200 with product data

### Requirement: Response time under 50ms for product listing
The product listing endpoint SHALL respond in under 50ms for catalogs up to 1000 products. This is achieved via indexed queries and pagination.

#### Scenario: Performance within budget
- **WHEN** `GET /v1/products` is called against a database with 500 products
- **THEN** the response time is under 50ms
