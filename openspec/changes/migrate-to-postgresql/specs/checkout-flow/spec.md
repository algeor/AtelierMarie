## MODIFIED Requirements

### Requirement: Checkout converts cart to order atomically
The system SHALL expose `POST /v1/orders` accepting customer_email, customer_name (optional), delivery details (optional), and notes (optional). The endpoint SHALL open a PostgreSQL transaction, acquire row-level locks on every product in the cart via `SELECT ... FOR UPDATE ORDER BY id ASC`, then atomically validate stock, create an order with status `pending`, snapshot product names and prices into `order_items`, decrement product stock, and clear the session's cart — all within that transaction. On success it SHALL return the created order with HTTP 201. All exceptions within the transaction SHALL be caught specifically (`asyncpg.exceptions.UniqueViolationError`, `asyncpg.exceptions.CheckViolationError`, `asyncpg.exceptions.DeadlockDetectedError`) with proper chaining and logging. Deadlocks SHALL be retried once before surfacing.

#### Scenario: Successful checkout with multiple items
- **WHEN** a session with 2 cart items (product A qty 2, product B qty 1) sends `POST /v1/orders` with a valid email, and both products have sufficient stock
- **THEN** an order is created with status `pending`, `total_cents` equals (A.price_cents × 2 + B.price_cents × 1), order_items contain snapshots of current product names and prices, product A stock decreases by 2, product B stock decreases by 1, cart_items for this session are deleted, and the response is HTTP 201 with full order details

#### Scenario: Checkout with empty cart fails
- **WHEN** a session with no cart items sends `POST /v1/orders`
- **THEN** the API returns HTTP 400 with error code `EMPTY_CART` and message "Cart is empty", no order is created

#### Scenario: Checkout with insufficient stock fails
- **WHEN** a session has product X with quantity 5 in cart but product X has only 2 in stock at lock time
- **THEN** the API returns HTTP 409 with error details identifying product X, requested quantity 5, and available quantity 2; no order is created; the transaction rolls back; cart is unchanged; stock is unchanged

#### Scenario: Race condition — two checkouts for last item are serialized by row lock
- **WHEN** two concurrent sessions each have the last unit of product X in their cart and both attempt checkout simultaneously
- **THEN** the first transaction acquires the `FOR UPDATE` lock on product X, validates stock=1, decrements to 0, and commits
- **AND** the second transaction blocks on the lock, then upon acquisition sees stock=0, rolls back, and its request receives HTTP 409
- **AND** product X's final stock is 0, never negative

#### Scenario: Multi-product checkouts do not deadlock
- **WHEN** two concurrent checkouts each contain products X and Y but in opposite cart-add orders
- **THEN** both transactions lock products in the same ascending-id order (`X` before `Y` if `id(X) < id(Y)`) and no deadlock occurs — one completes first, the other blocks and then proceeds

#### Scenario: Deadlock is retried once
- **WHEN** a checkout transaction receives Postgres error `40P01` (deadlock detected) despite the ordering rule (e.g., due to lock escalation from another operation)
- **THEN** the service retries the transaction one time from the beginning; if the retry also fails, HTTP 409 is returned and the failure is logged at WARNING

#### Scenario: Read-only operations are not blocked by checkout
- **WHEN** a checkout transaction holds `FOR UPDATE` locks on some product rows
- **THEN** unrelated `GET /v1/products` and `GET /v1/products/{other_id}` requests complete normally — Postgres readers do not block on writer row locks unless they themselves take `FOR UPDATE`

#### Scenario: Checkout logs full operation lifecycle
- **WHEN** a checkout operation completes (success or failure)
- **THEN** structured logs are emitted with: operation start (session_id, item_count), stock validation result, and operation end (order_id or error type, duration_ms)

#### Scenario: Database operational error during checkout is logged and reported
- **WHEN** an unexpected `asyncpg.PostgresError` (e.g., connection loss mid-transaction) occurs during checkout
- **THEN** the transaction is rolled back by the `async with conn.transaction():` block, the error is logged at ERROR level with full context (session_id, operation="checkout", exc_info=True), and the API returns HTTP 500 with a generic error message (no internal details leaked)
