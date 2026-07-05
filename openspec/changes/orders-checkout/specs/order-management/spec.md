## ADDED Requirements

### Requirement: Get order by ID (authenticated)
The system SHALL return order details including all order_items when an authenticated user requests their own order by ID.

#### Scenario: Owner retrieves their order
- **WHEN** an authenticated user sends GET /v1/orders/{id} for an order where order.user_id matches their user ID
- **THEN** the system returns 200 with the full order object including items, status, total_price, and timestamps

#### Scenario: Non-owner attempts retrieval
- **WHEN** an authenticated user sends GET /v1/orders/{id} for an order belonging to a different user
- **THEN** the system returns 404 (not 403, to avoid leaking order existence)

### Requirement: Get order by ID (anonymous via session)
The system SHALL allow anonymous order retrieval when the request's X-Session-ID matches the order's session_id.

#### Scenario: Session-matched anonymous retrieval
- **WHEN** an unauthenticated request sends GET /v1/orders/{id} with X-Session-ID matching the order's session_id
- **THEN** the system returns 200 with the full order object

#### Scenario: Session mismatch
- **WHEN** an unauthenticated request sends GET /v1/orders/{id} with X-Session-ID that does not match the order's session_id
- **THEN** the system returns 404

#### Scenario: No session header on anonymous request
- **WHEN** an unauthenticated request sends GET /v1/orders/{id} without X-Session-ID header
- **THEN** the system returns 401 indicating authentication or session_id is required

### Requirement: List user orders
The system SHALL return a paginated list of orders for the authenticated user, ordered by creation date descending.

#### Scenario: Authenticated user lists orders
- **WHEN** an authenticated user sends GET /v1/orders
- **THEN** the system returns a paginated response with orders belonging to that user (newest first), including status and total_price but not full item details

#### Scenario: Pagination parameters
- **WHEN** a user sends GET /v1/orders?page=2&per_page=10
- **THEN** the system returns the second page of 10 orders with total count metadata

#### Scenario: Unauthenticated list request
- **WHEN** an unauthenticated request sends GET /v1/orders
- **THEN** the system returns 401

### Requirement: Update order status (admin)
The system SHALL allow admin users to update order status via PATCH /v1/orders/{id}/status, enforcing valid state transitions.

#### Scenario: Valid status transition
- **WHEN** an admin sends PATCH /v1/orders/{id}/status with {"status": "confirmed"} for an order in "pending" status
- **THEN** the system updates the order status to "confirmed", updates updated_at, and returns 200

#### Scenario: Invalid status transition
- **WHEN** an admin sends PATCH /v1/orders/{id}/status with {"status": "delivered"} for an order in "pending" status
- **THEN** the system returns 422 with error indicating the transition from "pending" to "delivered" is not allowed

#### Scenario: Terminal state rejection
- **WHEN** an admin sends PATCH /v1/orders/{id}/status with any status for an order in "cancelled" or "refunded" status
- **THEN** the system returns 422 indicating the order is in a terminal state

#### Scenario: Non-admin access denied
- **WHEN** a non-admin user sends PATCH /v1/orders/{id}/status
- **THEN** the system returns 403

### Requirement: Order status state machine
The system SHALL enforce the following valid status transitions: pending → {confirmed, cancelled}; confirmed → {shipped, cancelled, refunded}; shipped → {delivered}. The states delivered, cancelled, and refunded are terminal.

#### Scenario: All valid transitions from pending
- **WHEN** an order is in "pending" status
- **THEN** it can transition to "confirmed" or "cancelled" only

#### Scenario: All valid transitions from confirmed
- **WHEN** an order is in "confirmed" status
- **THEN** it can transition to "shipped", "cancelled", or "refunded" only

#### Scenario: All valid transitions from shipped
- **WHEN** an order is in "shipped" status
- **THEN** it can transition to "delivered" only

#### Scenario: Terminal states have no transitions
- **WHEN** an order is in "delivered", "cancelled", or "refunded" status
- **THEN** no further status transitions are allowed

### Requirement: Order data model
The system SHALL store orders with: id (auto-increment), user_id (nullable FK to users), session_id (required), payment_method (required, default "cod"), total_price, status, created_at, updated_at. Order items SHALL store: id (auto-increment), order_id (FK to orders), product_id (FK to products), quantity, price_at_purchase.

#### Scenario: Schema includes all required fields
- **WHEN** the orders and order_items tables are created
- **THEN** they include all specified columns with correct types, constraints, and foreign keys including payment_method TEXT NOT NULL DEFAULT 'cod'

### Requirement: Order state is never cached

The system SHALL always read order state directly from SQLite on every request. Orders are a stateful resource with transitions (pending → confirmed → shipped → delivered) that must reflect immediately. Caching introduces risk of showing stale status to customers or admins, which is unacceptable for a transactional system. SQLite WAL reads complete in <5ms, making caching unnecessary.

#### Scenario: Status change reflects immediately
- **WHEN** an admin updates an order status to "shipped"
- **AND** the customer immediately requests GET /v1/orders/{id}
- **THEN** the response shows the updated "shipped" status with no stale delay

#### Scenario: No in-memory caching layer applied to order endpoints
- **WHEN** the application serves GET /v1/orders, GET /v1/orders/{id}, or PATCH /v1/orders/{id}/status
- **THEN** every request reads from SQLite directly
- **AND** no TTL cache, response cache, or memoization layer is applied
