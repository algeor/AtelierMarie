## ADDED Requirements

### Requirement: Speedy client health check uses official Client Service
The Speedy integration SHALL provide a safe health check that calls official Speedy Client Service endpoints to verify credentials and sender client identity without creating or mutating shipments.

#### Scenario: Own client id returned
- **WHEN** the Speedy health check calls `POST BASE_URL/client` with configured credentials
- **THEN** the response client id is returned in an admin-safe result

#### Scenario: Configured client id comparison
- **WHEN** the returned Speedy client id does not match configured `speedy_client_id`
- **THEN** the health check reports a sender identity mismatch instead of reporting the integration as healthy

### Requirement: Speedy shipment lookup and information operations
The Speedy integration SHALL support official shipment lookup operations for admin diagnostics: finding parcels by local order reference and retrieving shipment information by shipment id.

#### Scenario: Find parcels by order reference
- **WHEN** an admin searches for a local order id/reference in the Speedy admin page
- **THEN** the system calls `POST BASE_URL/shipment/search` and returns matching Speedy parcel or shipment ids

#### Scenario: Fetch shipment information
- **WHEN** an admin requests details for a Speedy shipment id
- **THEN** the system calls `POST BASE_URL/shipment/info` and returns admin-safe shipment information

### Requirement: Speedy shipment cancellation operation
The Speedy integration SHALL support canceling a Speedy shipment through the official cancellation endpoint when local and courier state allow it. Cancellation failures SHALL be surfaced as typed operational errors and SHALL NOT silently mutate local order state.

#### Scenario: Cancel shipment accepted
- **WHEN** Speedy accepts a cancellation request for a shipment id
- **THEN** the system records the successful cancellation and returns an admin-safe success response

#### Scenario: Cancel shipment rejected
- **WHEN** Speedy returns an error for a cancellation request
- **THEN** the system maps the Speedy error context/message into a typed admin-safe error and leaves local order state unchanged

### Requirement: Speedy pickup operations
The Speedy integration SHALL support official pickup terms and pickup request operations for explicit admin pickup scheduling.

#### Scenario: Pickup terms requested
- **WHEN** pickup terms are requested for Speedy sender/payment context
- **THEN** the system calls `POST BASE_URL/pickup/terms` and returns available cutoff timestamps or a typed error

#### Scenario: Pickup request created
- **WHEN** an admin submits a pickup request with shipment scope, visit end time, contact, and phone
- **THEN** the system calls `POST BASE_URL/pickup` and returns the pickup orders from Speedy
