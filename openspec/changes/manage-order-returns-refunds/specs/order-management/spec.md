## MODIFIED Requirements

### Requirement: Order state machine enforces valid transitions
The system SHALL enforce the following state transitions: pending to confirmed or cancelled, confirmed to shipped or cancelled, shipped to delivered or return_in_transit, delivered to return_in_transit, and return_in_transit to returned. Any transition not in this list SHALL be rejected with HTTP 422. Terminal states returned and cancelled SHALL not allow further order-status transitions.

#### Scenario: Valid transition from pending to confirmed
- **WHEN** an admin updates order status from "pending" to "confirmed"
- **THEN** the order status is updated to "confirmed" and updated_at is refreshed

#### Scenario: Valid transition from pending to cancelled
- **WHEN** an admin updates order status from "pending" to "cancelled"
- **THEN** the order status is updated to "cancelled" and stock is restored for all order items

#### Scenario: Invalid transition from pending to shipped
- **WHEN** an admin attempts to update order status from "pending" to "shipped"
- **THEN** the API returns HTTP 422 with error "Invalid state transition from 'pending' to 'shipped'"

#### Scenario: Valid transition from shipped to return in transit
- **WHEN** an admin updates order status from "shipped" to "return_in_transit"
- **THEN** the order status is updated to "return_in_transit" and stock is not restored

#### Scenario: Valid transition from delivered to return in transit
- **WHEN** an admin updates order status from "delivered" to "return_in_transit"
- **THEN** the order status is updated to "return_in_transit" and stock is not restored

#### Scenario: Valid transition from return in transit to returned
- **WHEN** an admin updates order status from "return_in_transit" to "returned"
- **THEN** the order status is updated to "returned" and stock remains unchanged until inspection/restock action

#### Scenario: Invalid transition from returned terminal state
- **WHEN** an admin attempts to update a "returned" order to any other order status
- **THEN** the API returns HTTP 422 with error indicating returned is a terminal order state

#### Scenario: Invalid transition from cancelled terminal state
- **WHEN** an admin attempts to update a "cancelled" order to "pending"
- **THEN** the API returns HTTP 422 with error indicating cancelled is a terminal state

## ADDED Requirements

### Requirement: Post-shipment returns do not restore stock automatically
The system SHALL NOT restore stock when a shipped or delivered order enters `return_in_transit` or `returned`. Returned stock SHALL be restored only by an explicit inspection/restock action.

#### Scenario: Shipped order marked return in transit keeps stock unchanged
- **WHEN** an admin marks a shipped order as `return_in_transit`
- **THEN** product stock values for the order items remain unchanged

#### Scenario: Returned order keeps stock unchanged before inspection
- **WHEN** an admin marks a return in transit order as `returned`
- **THEN** product stock values remain unchanged until an admin records a restock decision
