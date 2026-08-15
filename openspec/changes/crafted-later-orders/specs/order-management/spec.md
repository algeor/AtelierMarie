## MODIFIED Requirements

### Requirement: Order state machine enforces valid transitions
The system SHALL enforce the following state transitions: pending → confirmed, pending → cancelled, confirmed → shipped, confirmed → cancelled, shipped → delivered. Any transition not in this list SHALL be rejected with HTTP 422. Terminal states (delivered, cancelled) SHALL not allow any further transitions. In addition, shipment SHALL be blocked unless the order's `fulfillment_status` is `ready`.

#### Scenario: Valid transition from pending to confirmed
- **WHEN** an admin updates order status from `pending` to `confirmed`
- **THEN** the order status is updated to `confirmed` and `updated_at` is refreshed

#### Scenario: Valid transition from pending to cancelled
- **WHEN** an admin updates order status from `pending` to `cancelled`
- **THEN** the order status is updated to `cancelled`
- **AND** any previously allocated stock is restored for all order items

#### Scenario: Invalid transition from pending to shipped
- **WHEN** an admin attempts to update order status from `pending` to `shipped`
- **THEN** the API returns HTTP 422 with error `Invalid state transition from 'pending' to 'shipped'`

#### Scenario: Shipment blocked while awaiting production
- **WHEN** an admin attempts to update order status from `confirmed` to `shipped` for an order with `fulfillment_status = awaiting_production`
- **THEN** the API returns HTTP 422
- **AND** the order remains `confirmed`

#### Scenario: Invalid transition from delivered (terminal)
- **WHEN** an admin attempts to update a `delivered` order to any other status
- **THEN** the API returns HTTP 422 with error indicating delivered is a terminal state

#### Scenario: Invalid transition from cancelled (terminal)
- **WHEN** an admin attempts to update a `cancelled` order to `pending`
- **THEN** the API returns HTTP 422 with error indicating cancelled is a terminal state

### Requirement: Stock restoration on cancellation
The system SHALL restore product stock when an order is cancelled, but only for quantities that were actually allocated to that order. This SHALL happen atomically in the same transaction as the status update.

#### Scenario: Cancel order restores allocated stock only
- **WHEN** an order line has `allocated_quantity = 2` and `backordered_quantity = 3` at cancellation time
- **THEN** product stock increases by `2`
- **AND** no stock is restored for the outstanding `3` units that were never allocated

#### Scenario: Cancel fully allocated order restores full quantity
- **WHEN** an order line has `allocated_quantity = 4` and `backordered_quantity = 0`
- **THEN** product stock increases by `4`

#### Scenario: Cancel from confirmed state also restores allocated stock
- **WHEN** a confirmed order is cancelled
- **THEN** the same allocated-only restoration rule applies
