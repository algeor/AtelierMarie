## ADDED Requirements

### Requirement: Checkout converts cart to order atomically
The system SHALL expose `POST /v1/orders` accepting customer_email, customer_name (optional), shipping_address (optional), and notes (optional). The endpoint SHALL atomically validate stock, create an order with status "pending", snapshot product names and prices into order_items, decrement product stock, and clear the session's cart — all within a single database transaction. On success it SHALL return the created order with HTTP 201.

#### Scenario: Successful checkout with multiple items
- **WHEN** a session with 2 cart items (product A qty 2, product B qty 1) sends `POST /v1/orders` with a valid email, and both products have sufficient stock
- **THEN** an order is created with status "pending", total_cents equals (A.price_cents × 2 + B.price_cents × 1), order_items contain snapshots of current product names and prices, product A stock decreases by 2, product B stock decreases by 1, cart_items for this session are deleted, and the response is HTTP 201 with full order details

#### Scenario: Checkout with empty cart fails
- **WHEN** a session with no cart items sends `POST /v1/orders`
- **THEN** the API returns HTTP 400 with error code "EMPTY_CART" and message "Cart is empty", no order is created

#### Scenario: Checkout with insufficient stock fails
- **WHEN** a session has product X with quantity 5 in cart but product X has only 2 in stock
- **THEN** the API returns HTTP 409 with error details identifying product X, requested quantity 5, and available quantity 2; no order is created, cart is unchanged, stock is unchanged

#### Scenario: Checkout validates all items and reports all failures
- **WHEN** a session has two products in cart, both with insufficient stock
- **THEN** the API returns HTTP 409 identifying ALL failing products (batch validation — all items checked, all failures returned in one response); no order is created, cart is unchanged, stock is unchanged

#### Scenario: Checkout with deactivated product fails
- **WHEN** a session has a product in cart that has been deactivated (`is_active = 0`) since being added
- **THEN** the API returns HTTP 409 with error code "PRODUCT_UNAVAILABLE" identifying the deactivated product; no order is created, cart is unchanged

#### Scenario: Race condition — two checkouts for last item
- **WHEN** two concurrent sessions each have the last unit of product X in their cart and both attempt checkout simultaneously
- **THEN** exactly one checkout succeeds (HTTP 201) and the other fails (HTTP 409) with "Insufficient stock"; product X stock ends at 0, not negative

### Requirement: Checkout validates request input
The system SHALL validate that customer_email is a valid email format, customer_name is at most 200 characters, shipping_address is at most 1000 characters, and notes is at most 2000 characters. Invalid input SHALL return HTTP 422.

#### Scenario: Invalid email format rejected
- **WHEN** a session sends `POST /v1/orders` with customer_email "not-an-email"
- **THEN** the API returns HTTP 422 with validation error details for the email field

#### Scenario: Overly long customer name rejected
- **WHEN** a session sends `POST /v1/orders` with customer_name exceeding 200 characters
- **THEN** the API returns HTTP 422 with validation error details for the customer_name field

### Requirement: Price snapshot is immutable
The system SHALL copy product name and price_cents into order_items at checkout time. Order item prices SHALL NOT change even if the product price is subsequently updated.

#### Scenario: Product price change does not affect existing orders
- **WHEN** an order is placed for product X at 2500 cents, and then product X price is updated to 3000 cents
- **THEN** retrieving the order still shows the order item price as 2500 cents

### Requirement: Order ID is a UUID
The system SHALL generate order IDs as UUID v4 strings. Order IDs SHALL be unguessable and not sequential.

#### Scenario: Created order has UUID format
- **WHEN** a successful checkout creates an order
- **THEN** the returned order ID matches UUID v4 format (8-4-4-4-12 hex pattern)

### Requirement: Total is server-computed
The system SHALL compute `total_cents` server-side as the sum of (price_cents × quantity) for all order items at checkout time. No client-provided total SHALL be accepted or used. The `CreateOrderRequest` SHALL NOT include a `total_cents` field.

#### Scenario: Server computes total from item prices and quantities
- **WHEN** a session checks out with product A (price_cents=1500, qty=2) and product B (price_cents=2000, qty=1)
- **THEN** the order total_cents equals 5000 (1500×2 + 2000×1), computed entirely server-side
