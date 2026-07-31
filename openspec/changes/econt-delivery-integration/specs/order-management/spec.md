## ADDED Requirements

### Requirement: Orders persist courier shipment metadata
Orders SHALL persist courier shipment metadata separately from delivery details, including courier provider, courier order id when available, shipment number, label URL, sync status, last synced timestamp, label creation timestamp, and redacted last error.

#### Scenario: Metadata persisted after label creation
- **WHEN** Econt `createAWB` returns shipment number and PDF URL
- **THEN** the order stores those values in courier shipment metadata fields

#### Scenario: Metadata included in order responses
- **WHEN** an order with Econt shipment metadata is retrieved by customer or admin
- **THEN** the response includes public-safe shipment number, tracking URL, and sync status fields

### Requirement: Econt fulfillment respects order state transitions
The system SHALL update local order status only through valid state-machine transitions when Econt fulfillment actions occur.

#### Scenario: AWB created for pending order
- **WHEN** AWB creation succeeds for a pending order
- **THEN** the system may move the order to confirmed if configured, but SHALL NOT directly transition pending to shipped

#### Scenario: Shipment trace indicates delivered
- **WHEN** Econt trace refresh indicates delivery and the local order is shipped
- **THEN** the system may transition the order to delivered if automatic delivery sync is enabled

#### Scenario: Invalid status transition prevented
- **WHEN** an Econt event would imply a transition forbidden by the local state machine
- **THEN** the system records the courier event without changing local order status
