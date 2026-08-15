## ADDED Requirements

### Requirement: Orders track fulfillment readiness separately from order status
The system SHALL track whether an accepted order is physically ready to ship using `fulfillment_status` with values `ready` and `awaiting_production`. This field SHALL be exposed in public and admin order responses. An order SHALL be `awaiting_production` when any line still has an outstanding quantity that has not yet been allocated from stock.

#### Scenario: Order with shortage starts awaiting production
- **WHEN** checkout accepts an order where at least one line cannot be fully allocated from current stock
- **THEN** the order is created successfully
- **AND** `fulfillment_status` is `awaiting_production`

#### Scenario: Fully allocated order starts ready
- **WHEN** checkout accepts an order where every line is fully allocated from current stock
- **THEN** `fulfillment_status` is `ready`

### Requirement: Order items snapshot allocated and backordered quantities
Each order item SHALL persist `allocated_quantity` and `backordered_quantity` alongside the ordered quantity. At all times, `allocated_quantity + backordered_quantity` SHALL equal the ordered quantity.

#### Scenario: Mixed line records both quantities
- **WHEN** a customer orders 5 units and only 2 can be allocated at checkout
- **THEN** the order item stores `quantity = 5`, `allocated_quantity = 2`, and `backordered_quantity = 3`

#### Scenario: Fully available line stores zero shortfall
- **WHEN** a customer orders 2 units and all 2 are available at checkout
- **THEN** the order item stores `allocated_quantity = 2` and `backordered_quantity = 0`

### Requirement: Admin can mark an awaiting-production order ready
The system SHALL provide an admin fulfillment action that converts an `awaiting_production` order to `ready` only after every outstanding `backordered_quantity` can be allocated from current stock. The action SHALL reserve those quantities atomically and update the order items so their `backordered_quantity` becomes `0`.

#### Scenario: Ready action succeeds when full order can now be allocated
- **WHEN** an admin marks an `awaiting_production` order ready and every outstanding line quantity is present in stock
- **THEN** the system reserves the outstanding quantities
- **AND** updates each line to `backordered_quantity = 0`
- **AND** sets `fulfillment_status = ready`

#### Scenario: Ready action fails if any outstanding quantity is still missing
- **WHEN** an admin marks an `awaiting_production` order ready but at least one outstanding quantity is still unavailable
- **THEN** the system rejects the action
- **AND** leaves the order in `awaiting_production`
