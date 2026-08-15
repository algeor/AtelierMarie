## ADDED Requirements

### Requirement: Admin order detail exposes fulfillment readiness and shortfall
Admin order detail responses SHALL include order-level `fulfillment_status` plus item-level `allocated_quantity` and `backordered_quantity` so the atelier can see what is already reserved and what still needs crafting.

#### Scenario: Admin sees mixed fulfillment quantities
- **WHEN** an admin opens an order where one line is partially allocated
- **THEN** the order detail shows the allocated and backordered quantities for that line
- **AND** displays the order `fulfillment_status`

### Requirement: Admin can mark an awaiting-production order ready
The admin order workflow SHALL provide an action that marks an order `ready` for shipment only after all outstanding `backordered_quantity` values can be allocated from current stock.

#### Scenario: Admin marks order ready after production
- **WHEN** all outstanding quantities are now available and an admin triggers the ready action
- **THEN** the order `fulfillment_status` becomes `ready`
- **AND** the reserved quantities are updated atomically

#### Scenario: Admin cannot ship before ready
- **WHEN** an order remains `awaiting_production`
- **THEN** shipping actions are blocked or rejected until the ready action succeeds
