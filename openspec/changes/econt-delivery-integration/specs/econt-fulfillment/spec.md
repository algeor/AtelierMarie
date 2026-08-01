## ADDED Requirements

### Requirement: Econt order payload is built from local order data
The system SHALL build an Econt `Order` payload from the local order, delivery details, order items, payment method, product weights, and Econt settings. The payload SHALL include order number, order time, order sum, currency, COD flag, shipment description, pack count, customer info, sender info when configured, and item summaries.

#### Scenario: Build payload for Econt office delivery
- **WHEN** an order uses Econt office delivery with `office_code` present
- **THEN** the generated `customerInfo` includes the recipient name, phone, email, city, and `officeCode`

#### Scenario: Build payload for Econt door delivery
- **WHEN** an order uses Econt door delivery
- **THEN** the generated `customerInfo` includes city, post code, address, phone, and email

#### Scenario: COD mapping
- **WHEN** an order has `payment_method='cod'`
- **THEN** the Econt payload has `cod=true` and uses the configured courier currency for the COD amount

#### Scenario: Non-COD mapping
- **WHEN** an order has `payment_method='card'` or `payment_method='bank_transfer'`
- **THEN** the Econt payload has `cod=false`

### Requirement: Admin can create an Econt AWB label
The system SHALL provide an admin-only action that calls `OrdersService.createAWB` for an eligible Econt order, persists the returned shipment number and label PDF URL, and updates local tracking fields using carrier `econt`.

#### Scenario: Create AWB succeeds
- **WHEN** an admin creates an AWB for a confirmed Econt order without an existing shipment number
- **THEN** the system calls Econt once, persists `courier_shipment_number`, `courier_label_url`, `tracking_number`, `tracking_carrier='econt'`, and `tracking_url`, and records a fulfillment event

#### Scenario: Create AWB blocked for non-Econt order
- **WHEN** an admin tries to create an Econt AWB for a Speedy order
- **THEN** the system rejects the action with an order-data validation error and no Econt request is made

#### Scenario: Create AWB blocked when office code is missing
- **WHEN** an Econt office-delivery order lacks `office_code`
- **THEN** the system rejects label creation and tells the admin to repair/select a valid Econt office before retrying

#### Scenario: Duplicate AWB prevented
- **WHEN** an order already has `courier_shipment_number`
- **THEN** the default create action does not call Econt again and returns the existing label metadata

### Requirement: Admin can update, delete, and retry Econt fulfillment actions
The system SHALL support updating an Econt order before label creation, deleting an Econt label when locally and courier-side safe, and retrying failed actions with redacted stored payload/error context.

#### Scenario: Update order before label creation
- **WHEN** an admin edits delivery details before AWB creation and clicks sync
- **THEN** the system calls `OrdersService.updateOrder`, stores the returned courier order id if present, and records the sync event

#### Scenario: Delete label before shipment leaves sender
- **WHEN** an admin deletes an Econt label for an order that is not shipped or delivered locally
- **THEN** the system calls `OrdersService.deleteLabel`, clears local label metadata on success, and records the deletion event

#### Scenario: Retry after transient Econt outage
- **WHEN** a previous Econt action failed due to timeout or 5xx
- **THEN** the admin can retry the action and the system uses the latest local order data

### Requirement: Econt fulfillment events are auditable
The system SHALL store action history and trace events for Econt fulfillment without storing secrets. Each event SHALL include order id, action, status, redacted request/response or error details, created timestamp, and actor when available.

#### Scenario: Fulfillment event recorded
- **WHEN** an admin creates an AWB
- **THEN** an `order_courier_events` row records the attempted action and final result

#### Scenario: Secret redaction in event payload
- **WHEN** an Econt request snapshot is stored
- **THEN** Authorization headers and private key values are absent or replaced with a redacted marker
