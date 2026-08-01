## ADDED Requirements

### Requirement: Checkout persists Econt fulfillment metadata
When checkout creates an Econt order, the system SHALL persist label-ready delivery metadata, including Econt office code for office delivery, while keeping all external Econt calls outside the checkout transaction.

#### Scenario: Econt office checkout persists office code
- **WHEN** a customer checks out with Econt office delivery
- **THEN** the created order's delivery details contain `office_code` in addition to `office_id`

#### Scenario: Checkout does not call Econt
- **WHEN** a customer places an order with Econt delivery
- **THEN** the checkout transaction completes without calling Econt Delivery APIs

#### Scenario: Missing Econt office code rejected at checkout
- **WHEN** a customer submits Econt office delivery with an office id but no office code and the selected office catalog has no code for that office
- **THEN** checkout rejects the delivery payload with a validation error rather than creating an order that cannot produce a label

### Requirement: Checkout records Econt fulfillment readiness
The order response SHALL include enough courier metadata for the frontend/admin to know whether Econt fulfillment is not configured, ready, blocked by validation, label-created, or failed.

#### Scenario: New Econt order is fulfillment ready
- **WHEN** checkout creates an Econt order and required Econt settings are configured
- **THEN** the order response indicates Econt fulfillment is ready but no shipment number exists yet

#### Scenario: Econt disabled
- **WHEN** checkout creates an Econt delivery order while Econt fulfillment is disabled
- **THEN** the order remains valid locally and fulfillment status indicates manual fulfillment is required
