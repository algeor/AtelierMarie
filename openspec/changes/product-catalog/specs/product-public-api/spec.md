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
