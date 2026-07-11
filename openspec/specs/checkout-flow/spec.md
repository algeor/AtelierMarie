## MODIFIED Requirements

### Requirement: Checkout converts cart to order atomically
The system SHALL expose `POST /v1/orders` accepting customer_email, customer_name (optional), shipping_address (optional), and notes (optional). The endpoint SHALL use `BEGIN IMMEDIATE` to acquire a write lock at transaction start, then atomically validate stock, create an order with status "pending", snapshot product names and prices into order_items, decrement product stock, and clear the session's cart — all within that transaction. On success it SHALL return the created order with HTTP 201. All exceptions within the transaction SHALL be caught specifically (`sqlite3.IntegrityError` for constraint violations, `sqlite3.OperationalError` for lock/disk errors) with proper chaining and logging.

#### Scenario: Successful checkout with multiple items
- **WHEN** a session with 2 cart items (product A qty 2, product B qty 1) sends `POST /v1/orders` with a valid email, and both products have sufficient stock
- **THEN** an order is created with status "pending", total_cents equals (A.price_cents × 2 + B.price_cents × 1), order_items contain snapshots of current product names and prices, product A stock decreases by 2, product B stock decreases by 1, cart_items for this session are deleted, and the response is HTTP 201 with full order details

#### Scenario: Checkout with empty cart fails
- **WHEN** a session with no cart items sends `POST /v1/orders`
- **THEN** the API returns HTTP 400 with error code "EMPTY_CART" and message "Cart is empty", no order is created

#### Scenario: Checkout with insufficient stock fails
- **WHEN** a session has product X with quantity 5 in cart but product X has only 2 in stock
- **THEN** the API returns HTTP 409 with error details identifying product X, requested quantity 5, and available quantity 2; no order is created, cart is unchanged, stock is unchanged

#### Scenario: Race condition — two checkouts for last item are serialized by BEGIN IMMEDIATE
- **WHEN** two concurrent sessions each have the last unit of product X in their cart and both attempt checkout simultaneously
- **THEN** the second transaction immediately receives SQLITE_BUSY (due to BEGIN IMMEDIATE lock), which results in HTTP 409; exactly one checkout succeeds, product X stock ends at 0, not negative

#### Scenario: Checkout logs full operation lifecycle
- **WHEN** a checkout operation completes (success or failure)
- **THEN** structured logs are emitted with: operation start (session_id, item_count), stock validation result, and operation end (order_id or error type, duration_ms)

#### Scenario: Database operational error during checkout is logged and reported
- **WHEN** a `sqlite3.OperationalError` occurs during checkout (e.g., disk full)
- **THEN** the transaction is rolled back, the error is logged at ERROR level with full context (session_id, operation="checkout", exc_info=True), and the API returns HTTP 500 with a generic error message (no internal details leaked)
