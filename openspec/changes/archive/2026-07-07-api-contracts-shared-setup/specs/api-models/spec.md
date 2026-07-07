## ADDED Requirements

### Requirement: Product response model defines the product shape
The system SHALL expose product data through a `ProductResponse` schema containing: id (str), name (str), description (str|None), price_cents (int), category (str|None), image_url (str|None), stock (int), is_active (bool), is_featured (bool), created_at (str), updated_at (str).

#### Scenario: All fields present
- **WHEN** a product is serialized to JSON
- **THEN** the response contains all defined fields with correct types, and price_cents is a positive integer representing cents

#### Scenario: Nullable fields
- **WHEN** a product has no description, category, or image
- **THEN** those fields are `null` in the response (not omitted)

### Requirement: Product list response includes pagination
The system SHALL wrap product lists in a `ProductListResponse` containing: products (list[ProductResponse]), total (int), page (int), limit (int).

#### Scenario: Paginated product listing
- **WHEN** a client requests products with page=2, limit=10
- **THEN** the response contains at most 10 products, total reflects the full count, and page=2

### Requirement: Product creation accepts validated input
The system SHALL accept product creation via `CreateProductRequest` containing: name (str, required), description (str|None), price_cents (int, >0, required), category (str|None), stock (int, >=0, required), is_active (bool, default true), is_featured (bool, default false).

#### Scenario: Valid product creation
- **WHEN** a request includes name, price_cents > 0, and stock >= 0
- **THEN** the request passes validation

#### Scenario: Invalid price rejected
- **WHEN** a request includes price_cents <= 0
- **THEN** validation fails with a descriptive error

### Requirement: Product update accepts partial input
The system SHALL accept product updates via `UpdateProductRequest` where all fields are optional. Only provided fields are updated.

#### Scenario: Partial update
- **WHEN** a request includes only `{price_cents: 1500}`
- **THEN** validation passes and only price_cents is flagged for update

### Requirement: Cart item response includes product details
The system SHALL expose cart items through `CartItemResponse` containing: product_id (str), product (ProductResponse), quantity (int), added_at (str).

#### Scenario: Cart item with embedded product
- **WHEN** a cart item is serialized
- **THEN** the full ProductResponse is nested under the `product` field

### Requirement: Cart response aggregates items with totals
The system SHALL expose the full cart through `CartResponse` containing: items (list[CartItemResponse]), total_cents (int), item_count (int).

#### Scenario: Cart with multiple items
- **WHEN** a cart contains 2 items (product A qty 2 at 1000 cents, product B qty 1 at 2500 cents)
- **THEN** total_cents = 4500 and item_count = 3

### Requirement: Add to cart request validates quantity
The system SHALL accept `AddToCartRequest` containing: product_id (str, required), quantity (int, >=1, default 1).

#### Scenario: Valid add to cart
- **WHEN** product_id is provided and quantity >= 1
- **THEN** validation passes

#### Scenario: Zero quantity rejected
- **WHEN** quantity is 0 or negative
- **THEN** validation fails

### Requirement: Update cart item request validates quantity
The system SHALL accept `UpdateCartItemRequest` containing: quantity (int, >=0). Quantity of 0 means remove item.

#### Scenario: Set quantity to zero removes item
- **WHEN** quantity is 0
- **THEN** validation passes (handler interprets as removal)

### Requirement: Order response includes status and items
The system SHALL expose orders through `OrderResponse` containing: id (str), status (str — one of pending|confirmed|shipped|delivered|cancelled), total_cents (int), customer_email (str), customer_name (str|None), shipping_address (str|None), items (list[OrderItemResponse]), created_at (str), updated_at (str).

#### Scenario: Order with items
- **WHEN** an order is serialized
- **THEN** each item in the items list contains product_id, product_name, price_cents, and quantity (snapshot at purchase time)

### Requirement: Order item response captures purchase-time data
The system SHALL expose order items through `OrderItemResponse` containing: product_id (str), product_name (str), price_cents (int), quantity (int).

#### Scenario: Price snapshot preserved
- **WHEN** a product's price changes after an order is placed
- **THEN** the order item still shows the price_cents at purchase time

### Requirement: Create order request captures customer details
The system SHALL accept `CreateOrderRequest` containing: customer_email (str, valid email, required), customer_name (str|None), shipping_address (str|None), notes (str|None).

#### Scenario: Valid order creation
- **WHEN** customer_email is a valid email
- **THEN** validation passes

#### Scenario: Invalid email rejected
- **WHEN** customer_email is not a valid email format
- **THEN** validation fails with a descriptive error

### Requirement: Order list response includes pagination
The system SHALL wrap order lists in `OrderListResponse` containing: orders (list[OrderResponse]), total (int), page (int), limit (int).

#### Scenario: Paginated order list
- **WHEN** a user requests their orders with page=1, limit=20
- **THEN** the response contains at most 20 orders with total reflecting their full order count

### Requirement: User response exposes profile data
The system SHALL expose user profiles through `UserResponse` containing: id (str), email (str), name (str|None), avatar_url (str|None), is_admin (bool).

#### Scenario: User with all fields
- **WHEN** a user with Google profile data is serialized
- **THEN** name and avatar_url reflect the Google profile values

### Requirement: Auth token response provides JWT
The system SHALL expose authentication results through `AuthTokenResponse` containing: access_token (str), token_type (str, always "bearer"), user (UserResponse).

#### Scenario: Successful login
- **WHEN** a user completes OAuth login
- **THEN** the response includes a JWT access_token and the user's profile

### Requirement: Google OAuth callback request carries the code
The system SHALL accept `GoogleAuthRequest` containing: code (str, required), redirect_uri (str, required).

#### Scenario: Valid OAuth callback
- **WHEN** code and redirect_uri are provided
- **THEN** validation passes

### Requirement: Error response has consistent structure
The system SHALL return all errors in a standardized `ErrorResponse` shape containing: error.code (str, machine-readable), error.message (str, human-readable), error.details (object|None, contextual data like validation errors).

#### Scenario: Validation error
- **WHEN** a request fails Pydantic validation
- **THEN** the response body matches `{"error": {"code": "VALIDATION_ERROR", "message": "...", "details": {...}}}`

#### Scenario: Not found error
- **WHEN** a requested resource does not exist
- **THEN** the response body matches `{"error": {"code": "NOT_FOUND", "message": "...", "details": null}}`

#### Scenario: Unauthorized error
- **WHEN** a request lacks valid authentication for a protected endpoint
- **THEN** the response body matches `{"error": {"code": "UNAUTHORIZED", "message": "...", "details": null}}`

### Requirement: Pagination parameters are validated
The system SHALL accept pagination via `PaginationParams` containing: page (int, >=1, default 1), limit (int, 1-100, default 20).

#### Scenario: Default pagination
- **WHEN** no pagination parameters are provided
- **THEN** page defaults to 1 and limit defaults to 20

#### Scenario: Limit capped at 100
- **WHEN** limit > 100 is requested
- **THEN** validation fails (not silently capped)

### Requirement: Admin product import accepts CSV shape
The system SHALL accept `ProductImportRequest` containing: products (list[CreateProductRequest]) for bulk import.

#### Scenario: Bulk import of 50 products
- **WHEN** a list of 50 valid CreateProductRequest objects is provided
- **THEN** validation passes for the entire batch

### Requirement: Order status update validates transitions
The system SHALL accept `UpdateOrderStatusRequest` containing: status (str, must be one of pending|confirmed|shipped|delivered|cancelled).

#### Scenario: Valid status value
- **WHEN** status is "confirmed"
- **THEN** validation passes (transition validity is a service-layer concern, not model-level)

#### Scenario: Invalid status value
- **WHEN** status is "unknown_status"
- **THEN** validation fails
