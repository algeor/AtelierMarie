## ADDED Requirements

### Requirement: Econt trace can be refreshed
The system SHALL provide an admin action that calls Econt `OrdersService.getTrace` for orders with an Econt shipment number, persists returned trace events, and updates public-safe tracking summary fields.

#### Scenario: Trace refresh succeeds
- **WHEN** an admin refreshes trace for an Econt order with a shipment number
- **THEN** the system stores the latest trace events and updates the order's last synced timestamp

#### Scenario: Trace refresh without shipment number rejected
- **WHEN** an admin refreshes trace for an Econt order without a shipment number
- **THEN** the system rejects the action without calling Econt

### Requirement: Customers can view public Econt tracking details
Customer order pages SHALL show Econt shipment number, tracking URL, and high-level trace state when available. Raw courier payloads and operational errors SHALL remain admin-only.

#### Scenario: Public tracking available
- **WHEN** an Econt order has tracking events
- **THEN** the customer order detail page shows the latest public-safe tracking status and tracking link

#### Scenario: Courier error hidden from customer
- **WHEN** the last Econt trace refresh failed
- **THEN** the customer page does not show the raw error; the admin page shows the operational error
