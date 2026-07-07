## ADDED Requirements

### Requirement: Product name must not be empty and has max length
The system SHALL reject product creation/update requests where `name` is an empty string, whitespace-only, or exceeds 200 characters.

#### Scenario: Empty product name rejected
- **WHEN** a `POST /v1/admin/products` request has `name: ""`
- **THEN** the system returns 422 with a validation error indicating name must be at least 1 character

#### Scenario: Whitespace-only product name rejected
- **WHEN** a `POST /v1/admin/products` request has `name: "   "`
- **THEN** the system returns 422 with a validation error indicating name must contain non-whitespace characters

#### Scenario: Product name at max length accepted
- **WHEN** a `POST /v1/admin/products` request has `name` of exactly 200 characters
- **THEN** the system accepts the request (no validation error for name)

#### Scenario: Product name exceeding max length rejected
- **WHEN** a `POST /v1/admin/products` request has `name` of 201 characters
- **THEN** the system returns 422 with a validation error indicating max length exceeded

### Requirement: Product ID must be a valid slug
The system SHALL validate that product IDs match the pattern `^[a-z0-9]+(-[a-z0-9]+)*$` (lowercase alphanumeric segments separated by single hyphens, no leading/trailing/consecutive hyphens) and have length between 3 and 100 characters.

Note: This tightens the existing `min_length=1` to `min_length=3`. This is safe because the system is pre-production (no products exist in any database yet — only test fixtures). The minimum of 3 ensures meaningful, readable slugs (e.g., `wax`, `oil`) rather than cryptic single-character IDs.

#### Scenario: Valid slug accepted
- **WHEN** a product creation request has `id: "lavender-dream-300ml"`
- **THEN** the system accepts the ID

#### Scenario: Uppercase slug rejected
- **WHEN** a product creation request has `id: "Lavender-Dream"`
- **THEN** the system returns 422 indicating ID must be lowercase

#### Scenario: Slug starting with hyphen rejected
- **WHEN** a product creation request has `id: "-lavender"`
- **THEN** the system returns 422 indicating invalid ID format

#### Scenario: Slug with consecutive hyphens rejected
- **WHEN** a product creation request has `id: "lavender--dream"`
- **THEN** the system returns 422 indicating invalid ID format

#### Scenario: Empty ID rejected
- **WHEN** a product creation request has `id: ""`
- **THEN** the system returns 422 indicating ID must be at least 3 characters

### Requirement: Price in cents must be positive and bounded
The system SHALL validate that `price_cents` is a positive integer not exceeding 9,999,999 (€99,999.99). Zero and negative values MUST be rejected.

#### Scenario: Negative price rejected
- **WHEN** a product request has `price_cents: -100`
- **THEN** the system returns 422 indicating price must be greater than 0

#### Scenario: Zero price rejected
- **WHEN** a product request has `price_cents: 0`
- **THEN** the system returns 422 indicating price must be greater than 0

#### Scenario: Price at upper bound accepted
- **WHEN** a product request has `price_cents: 9999999`
- **THEN** the system accepts the request

#### Scenario: Price exceeding upper bound rejected
- **WHEN** a product request has `price_cents: 10000000`
- **THEN** the system returns 422 indicating price exceeds maximum

### Requirement: Cart quantity must be within bounds
The system SHALL validate cart item quantities differently for add vs. update operations:
- **Add to cart** (`AddToCartRequest`): quantity MUST be between 1 and 10 (inclusive). The max-per-item limit (10) is defined in config.
- **Update cart item** (`UpdateCartItemRequest`): quantity MUST be between 0 and 10 (inclusive). Quantity 0 means "remove item from cart" (existing design decision from session-cart spec).

Note: The existing `app/models/cart.py` has a placeholder `le=99` which is corrected to `le=10` per the architectural decision (luxury candles are not bulk-ordered). This is safe because the system is pre-production (all route handlers return 501 stubs). No migration logic is required. If the system were live, a migration plan would be needed to cap existing cart items at the new limit.

#### Scenario: Zero quantity rejected on add
- **WHEN** an `add_to_cart` request has `quantity: 0`
- **THEN** the system returns 422 indicating quantity must be at least 1

#### Scenario: Zero quantity on update removes item
- **WHEN** an `update_cart_item` request has `quantity: 0`
- **THEN** the system removes the item from the cart (DELETE row) and returns the updated cart

#### Scenario: Negative quantity rejected
- **WHEN** an `add_to_cart` or `update_cart_item` request has `quantity: -1`
- **THEN** the system returns 422 indicating quantity must be at least 0 (update) or 1 (add)

#### Scenario: Quantity exceeding per-item max rejected
- **WHEN** an `add_to_cart` or `update_cart_item` request has `quantity: 11` (max is 10)
- **THEN** the system returns 422 indicating quantity exceeds per-item limit

### Requirement: String fields have max length constraints
The system SHALL enforce maximum lengths on all string input fields:
- `description`: max 5,000 characters
- `category`: max 100 characters
- `email`: max 320 characters (RFC 5321)
- `customer_name`: max 200 characters

Note: String fields are stored as-is (no HTML sanitization at the backend layer). The frontend is responsible for safe rendering via default React/JSX escaping. If rich text (Markdown/HTML) support is ever added to descriptions, server-side allowlist-based sanitization MUST be added before storage.

#### Scenario: Description exceeding max length rejected
- **WHEN** a product request has `description` of 5,001 characters
- **THEN** the system returns 422 indicating description exceeds maximum length

#### Scenario: Email at max length accepted
- **WHEN** a checkout request has `customer_email` of exactly 320 characters (valid format)
- **THEN** the system accepts the email field

### Requirement: Stock must be non-negative integer
The system SHALL validate that `stock` values on product creation/update are non-negative integers not exceeding 1,000,000.

#### Scenario: Negative stock rejected
- **WHEN** an admin sets product stock to `-5`
- **THEN** the system returns 422 indicating stock must be non-negative

#### Scenario: Stock at upper bound accepted
- **WHEN** an admin sets product stock to `1000000`
- **THEN** the system accepts the request

#### Scenario: Stock exceeding upper bound rejected
- **WHEN** an admin sets product stock to `1000001`
- **THEN** the system returns 422 indicating stock exceeds maximum

### Requirement: Pagination parameters validated
The system SHALL validate pagination query parameters: `page` must be ≥1, `limit` must be between 1 and 100 (inclusive).

#### Scenario: Page zero rejected
- **WHEN** a list request has `?page=0`
- **THEN** the system returns 422 indicating page must be at least 1

#### Scenario: Negative page rejected
- **WHEN** a list request has `?page=-1`
- **THEN** the system returns 422 indicating page must be at least 1

#### Scenario: Limit exceeding max rejected
- **WHEN** a list request has `?limit=101`
- **THEN** the system returns 422 indicating limit must not exceed 100

#### Scenario: Limit zero rejected
- **WHEN** a list request has `?limit=0`
- **THEN** the system returns 422 indicating limit must be at least 1
