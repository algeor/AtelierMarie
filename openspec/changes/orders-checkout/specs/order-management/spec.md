## ADDED Requirements

### Requirement: List own orders
The system SHALL expose `GET /v1/orders` that returns a paginated list of orders belonging to the current session or authenticated user. Orders SHALL be sorted by `created_at` descending (newest first). Pagination SHALL use `?page=1&limit=20` query parameters.

#### Scenario: List orders for session with orders
- **WHEN** a session that has placed 3 orders sends `GET /v1/orders`
- **THEN** the API returns all 3 orders sorted newest-first with total count, page, and limit in the response

#### Scenario: List orders with pagination
- **WHEN** a session with 25 orders sends `GET /v1/orders?page=2&limit=10`
- **THEN** the API returns orders 11–20 (sorted by created_at desc), total=25, page=2, limit=10

#### Scenario: List orders for session with no orders
- **WHEN** a session that has never placed an order sends `GET /v1/orders`
- **THEN** the API returns an empty orders list with total=0

#### Scenario: Authenticated user sees orders from all their sessions
- **WHEN** a logged-in user who has placed orders across 2 different sessions sends `GET /v1/orders`
- **THEN** the API returns orders from both sessions (matched via user_id on the orders)

### Requirement: Get order detail
The system SHALL expose `GET /v1/orders/{id}` that returns full order details including all order items. Access SHALL be restricted to the session or user that owns the order.

#### Scenario: Owner retrieves order by ID
- **WHEN** the session that created order "abc-123" sends `GET /v1/orders/abc-123`
- **THEN** the API returns full order details including id, status, total_cents, customer_email, items (with product_id, product_name, price_cents, quantity), created_at, and updated_at

#### Scenario: Different session denied access
- **WHEN** a session that did NOT create order "abc-123" (and is not the linked user) sends `GET /v1/orders/abc-123`
- **THEN** the API returns HTTP 404 (not 403, to avoid leaking order existence)

#### Scenario: Authenticated user accesses order from old session
- **WHEN** a user who placed order "abc-123" while logged in now accesses it from a new session but same user account
- **THEN** the API returns the full order details (matched via user_id)

#### Scenario: Non-existent order returns 404
- **WHEN** any session sends `GET /v1/orders/nonexistent-id`
- **THEN** the API returns HTTP 404

### Requirement: Order state machine enforces valid transitions
The system SHALL enforce the following state transitions: pending → confirmed, pending → cancelled, confirmed → shipped, confirmed → cancelled, shipped → delivered. Any transition not in this list SHALL be rejected with HTTP 422. Terminal states (delivered, cancelled) SHALL not allow any further transitions.

#### Scenario: Valid transition from pending to confirmed
- **WHEN** an admin updates order status from "pending" to "confirmed"
- **THEN** the order status is updated to "confirmed" and updated_at is refreshed

#### Scenario: Valid transition from pending to cancelled
- **WHEN** an admin updates order status from "pending" to "cancelled"
- **THEN** the order status is updated to "cancelled" and stock is restored for all order items

#### Scenario: Invalid transition from pending to shipped
- **WHEN** an admin attempts to update order status from "pending" to "shipped"
- **THEN** the API returns HTTP 422 with error "Invalid state transition from 'pending' to 'shipped'"

#### Scenario: Invalid transition from delivered (terminal)
- **WHEN** an admin attempts to update a "delivered" order to any other status
- **THEN** the API returns HTTP 422 with error indicating delivered is a terminal state

#### Scenario: Invalid transition from cancelled (terminal)
- **WHEN** an admin attempts to update a "cancelled" order to "pending"
- **THEN** the API returns HTTP 422 with error indicating cancelled is a terminal state

### Requirement: Stock restoration on cancellation
The system SHALL restore product stock when an order is cancelled. For each item in the cancelled order, the product's stock SHALL be incremented by the order item quantity. This SHALL happen atomically in the same transaction as the status update.

#### Scenario: Cancel order restores stock
- **WHEN** an order with 2 units of product A and 3 units of product B is cancelled
- **THEN** product A stock increases by 2 and product B stock increases by 3, all within the same transaction

#### Scenario: Cancel order for deactivated product still restores stock
- **WHEN** an order containing a product that has since been deactivated is cancelled
- **THEN** the stock is still restored to the (inactive) product row

#### Scenario: Cancel from confirmed state also restores stock
- **WHEN** a confirmed order with 2 units of product A is cancelled
- **THEN** product A stock increases by 2 (stock restoration applies regardless of whether cancellation is from pending or confirmed)
