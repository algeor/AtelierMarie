## ADDED Requirements

### Requirement: Delivered orders record a delivery timestamp
When an order transitions to `delivered`, the system SHALL stamp a `delivered_at`
timestamp on the order. This timestamp anchors the return eligibility window and SHALL
NOT change on subsequent edits. Existing delivered orders without `delivered_at` SHALL
be backfilled exactly once from their delivered-transition time, falling back to
`updated_at` only for rows with no better source.

#### Scenario: Delivery stamps delivered_at
- **WHEN** an admin transitions an order from `shipped` to `delivered`
- **THEN** `delivered_at` is set to the transition time

#### Scenario: delivered_at is stable across later edits
- **WHEN** a delivered order is edited after delivery
- **THEN** `delivered_at` remains the original delivery time

#### Scenario: Legacy delivered orders are backfilled once
- **WHEN** the migration runs against a delivered order that predates the `delivered_at` column
- **THEN** `delivered_at` is populated from the best available source (`updated_at` as fallback) and is not overwritten on later runs

## MODIFIED Requirements

### Requirement: Order state machine enforces valid transitions
The system SHALL enforce the following state transitions: pending → confirmed, pending
→ cancelled, confirmed → shipped, confirmed → cancelled, shipped → delivered. Any
transition not in this list SHALL be rejected with HTTP 422. Terminal states
(delivered, cancelled) SHALL not allow any further transitions. A return against a
delivered order SHALL NOT reopen or change `orders.status`; `delivered` remains
terminal for fulfillment and returns are tracked on their own `returns` records.

#### Scenario: Valid transition from pending to confirmed
- **WHEN** an admin updates order status from "pending" to "confirmed"
- **THEN** the order status is updated to "confirmed" and updated_at is refreshed

#### Scenario: Delivered remains terminal despite a return
- **WHEN** a return is requested, approved, received, and refunded against a delivered order
- **THEN** the order's fulfillment status remains `delivered` throughout

#### Scenario: Invalid transition from delivered (terminal)
- **WHEN** an admin attempts to update a "delivered" order to any other status
- **THEN** the API returns HTTP 422 with error indicating delivered is a terminal state

### Requirement: Get order detail
The system SHALL expose `GET /v1/orders/{id}` that returns full order details including
all order items. Access SHALL be restricted to the session or user that owns the order.
For each line item, the response SHALL include the quantity already returned across
non-rejected/non-cancelled returns, and the order SHALL indicate whether it is
currently returnable (delivered and within the return window with remaining quantity).

#### Scenario: Owner retrieves order by ID
- **WHEN** the session that created order "abc-123" sends `GET /v1/orders/abc-123`
- **THEN** the API returns full order details including id, status, total_cents, customer_email, items (with product_id, product_name, price_cents, quantity), created_at, and updated_at

#### Scenario: Delivered order exposes returnable quantities
- **WHEN** the owning session fetches a delivered order within the return window where 1 of 2 units of an item was already refunded
- **THEN** each item reports its remaining returnable quantity (1 for that item) and the order is marked returnable

#### Scenario: Different session denied access
- **WHEN** a session that did NOT create order "abc-123" (and is not the linked user) sends `GET /v1/orders/abc-123`
- **THEN** the API returns HTTP 404 (not 403, to avoid leaking order existence)
