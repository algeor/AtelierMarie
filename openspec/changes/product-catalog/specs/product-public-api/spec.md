## ADDED Requirements

### Requirement: Public users can list active products
The system SHALL accept a GET request to `/v1/products` and return a paginated list of active products only (`is_active = TRUE`). The system SHALL support query parameters: `page` (default 1), `per_page` (default 20, max 100), `category` (filter).

#### Scenario: List active products
- **WHEN** any user sends GET `/v1/products`
- **THEN** system returns only products where `is_active = TRUE`, with pagination metadata

#### Scenario: Filter by category
- **WHEN** any user sends GET `/v1/products?category=electronics`
- **THEN** system returns only active products in the "electronics" category

#### Scenario: No auth required
- **WHEN** any user sends GET `/v1/products` without an Authorization header
- **THEN** system returns 200 OK with products (no authentication check)

#### Scenario: Inactive products hidden
- **WHEN** products exist with `is_active = FALSE`
- **THEN** those products SHALL NOT appear in the `/v1/products` response

### Requirement: Public users can get a single active product
The system SHALL accept a GET request to `/v1/products/{id}` and return the product only if it is active.

#### Scenario: Get active product
- **WHEN** any user sends GET `/v1/products/blue-widget` and the product is active
- **THEN** system returns the product with 200 OK

#### Scenario: Get inactive product returns 404
- **WHEN** any user sends GET `/v1/products/blue-widget` and the product has `is_active = FALSE`
- **THEN** system returns 404 Not Found (does not reveal the product exists)

#### Scenario: Get non-existent product
- **WHEN** any user sends GET `/v1/products/no-such-product`
- **THEN** system returns 404 Not Found

### Requirement: Public product search endpoint
The system SHALL expose `GET /v1/products/search?q={query}` that performs case-insensitive text search across product name, description, and category fields. Results SHALL be limited to active products and ranked by relevance (name match > description match > category match).

#### Scenario: Search returns matching products
- **WHEN** a client sends GET `/v1/products/search?q=vanilla`
- **THEN** products containing "vanilla" in name, description, or category are returned, ordered by relevance

#### Scenario: Search with no results
- **WHEN** a client sends GET `/v1/products/search?q=xyznonexistent`
- **THEN** the API returns HTTP 200 with an empty results array and `total: 0`

#### Scenario: Search excludes inactive products
- **WHEN** an inactive product matches the search query
- **THEN** it is NOT included in search results

#### Scenario: Empty query returns validation error
- **WHEN** a client sends GET `/v1/products/search?q=` (empty query)
- **THEN** the API returns HTTP 422 indicating query parameter is required

### Requirement: Stock quantity validation for cart operations
The system SHALL expose stock availability information in product responses and enforce stock limits when other services (cart, checkout) validate against the product catalog. The `stock_quantity` field SHALL be included in product responses.

#### Scenario: Product with stock shows available quantity
- **WHEN** a product with stock_quantity=5 is retrieved via GET `/v1/products/{slug}`
- **THEN** the response includes `stock_quantity: 5`

#### Scenario: Out-of-stock product visible but flagged
- **WHEN** an active product has stock_quantity=0
- **THEN** it appears in listings with `stock_quantity: 0` and `in_stock: false`

### Requirement: Atomic stock decrement service
The system SHALL provide an internal service function `decrement_stock(product_id: int, quantity: int) -> bool` that atomically decrements stock_quantity. It SHALL return False (and not decrement) if current stock is insufficient.

#### Scenario: Sufficient stock decremented
- **WHEN** `decrement_stock(product_id=5, quantity=2)` is called and product 5 has stock_quantity=5
- **THEN** stock_quantity is atomically updated to 3 and True is returned

#### Scenario: Insufficient stock rejected
- **WHEN** `decrement_stock(product_id=5, quantity=10)` is called and product 5 has stock_quantity=3
- **THEN** stock_quantity is NOT modified and False is returned

#### Scenario: Concurrent decrement safety
- **WHEN** two concurrent requests both attempt to decrement stock for the same product
- **THEN** SQLite's transaction serialization ensures only one succeeds if stock is insufficient for both
