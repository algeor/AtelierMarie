## ADDED Requirements

### Requirement: Admin list all orders
The system SHALL expose `GET /v1/admin/orders` that returns a paginated list of ALL orders across all sessions/users. This endpoint SHALL require admin authentication (JWT with is_admin=true OR valid API key). Orders SHALL be sorted by `created_at` descending. The endpoint SHALL support filtering by status via `?status=pending` query parameter.

#### Scenario: Admin lists all orders without filter
- **WHEN** an authenticated admin sends `GET /v1/admin/orders`
- **THEN** the API returns all orders from all customers, paginated, sorted newest-first

#### Scenario: Admin filters orders by status
- **WHEN** an authenticated admin sends `GET /v1/admin/orders?status=pending`
- **THEN** the API returns only orders with status "pending", paginated

#### Scenario: Admin lists orders with pagination
- **WHEN** an admin sends `GET /v1/admin/orders?page=2&limit=10`
- **THEN** the API returns the second page of 10 orders with correct total count

#### Scenario: Non-admin access denied
- **WHEN** a non-admin session sends `GET /v1/admin/orders`
- **THEN** the API returns HTTP 403

#### Scenario: Unauthenticated access denied
- **WHEN** a request without admin credentials sends `GET /v1/admin/orders`
- **THEN** the API returns HTTP 403

### Requirement: Admin get order detail
The system SHALL expose `GET /v1/admin/orders/{id}` that returns full order details including all items, customer info, shipping address, and notes. This endpoint SHALL require admin authentication. This allows admins to view any order regardless of session ownership for fulfillment purposes.

#### Scenario: Admin retrieves any order by ID
- **WHEN** an authenticated admin sends `GET /v1/admin/orders/abc-123`
- **THEN** the API returns full order details including items, customer_email, customer_name, shipping_address, and notes

#### Scenario: Admin retrieves non-existent order
- **WHEN** an authenticated admin sends `GET /v1/admin/orders/nonexistent`
- **THEN** the API returns HTTP 404

#### Scenario: Non-admin cannot access admin order detail
- **WHEN** a non-admin session sends `GET /v1/admin/orders/abc-123`
- **THEN** the API returns HTTP 403

### Requirement: Admin update order status
The system SHALL expose `PATCH /v1/admin/orders/{id}/status` accepting a JSON body with `status` field. This endpoint SHALL require admin authentication. The status transition SHALL be validated against the order state machine. On cancellation, stock SHALL be restored.

#### Scenario: Admin confirms a pending order
- **WHEN** an authenticated admin sends `PATCH /v1/admin/orders/abc-123/status` with `{"status": "confirmed"}`
- **THEN** the order status is updated to "confirmed", updated_at is refreshed, and the updated order is returned

#### Scenario: Admin cancels order and stock is restored
- **WHEN** an authenticated admin cancels an order containing 3 units of product X
- **THEN** the order status becomes "cancelled" and product X stock increases by 3

#### Scenario: Admin attempts invalid transition
- **WHEN** an authenticated admin sends `PATCH /v1/admin/orders/abc-123/status` with `{"status": "shipped"}` but order is in "pending" state
- **THEN** the API returns HTTP 422 with error describing the invalid transition

#### Scenario: Admin updates non-existent order
- **WHEN** an authenticated admin sends `PATCH /v1/admin/orders/nonexistent/status`
- **THEN** the API returns HTTP 404

#### Scenario: Non-admin cannot update order status
- **WHEN** a non-admin session sends `PATCH /v1/admin/orders/abc-123/status`
- **THEN** the API returns HTTP 403
