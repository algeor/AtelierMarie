## ADDED Requirements

### Requirement: Confirmation page explains crafted-later fulfillment when applicable
The order confirmation page SHALL show fulfillment guidance when the order's `fulfillment_status` is `awaiting_production`. The message SHALL make clear that the order was accepted and paid, but shipment will happen only after the full order is ready.

#### Scenario: Crafted-later confirmation copy
- **WHEN** a confirmation page renders an order with `fulfillment_status = awaiting_production`
- **THEN** the page explains that some items will be crafted after purchase
- **AND** states that the order ships only when complete

#### Scenario: Ready order omits crafted-later warning
- **WHEN** a confirmation page renders an order with `fulfillment_status = ready`
- **THEN** no crafted-later warning is shown
