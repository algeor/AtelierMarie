## ADDED Requirements

### Requirement: Dedicated Speedy admin page
The system SHALL provide a dedicated `/admin/speedy` page for Speedy operational health, fulfillment queues, shipment tools, pickup planning, and audit visibility. The page SHALL require admin authentication and SHALL NOT expose Speedy credentials or raw secret-bearing request payloads.

#### Scenario: Admin opens Speedy page
- **WHEN** an authenticated admin navigates to `/admin/speedy`
- **THEN** the page displays Speedy connection health, configuration summary, recent Speedy order queues, and available fulfillment actions

#### Scenario: Non-admin cannot open Speedy page
- **WHEN** a non-admin or unauthenticated user navigates to `/admin/speedy`
- **THEN** the user is denied by the existing admin route protection

### Requirement: Phase 1 Speedy health and configuration summary
The Speedy admin page SHALL show whether required Speedy configuration is present, whether `speedy_client_id` is numeric, whether the Speedy Client Service accepts the credentials, and whether the returned client id matches the configured sender client id. The health check SHALL use safe official Client Service endpoints and SHALL NOT create a shipment.

#### Scenario: Healthy Speedy configuration
- **WHEN** Speedy credentials are configured and the official Client Service returns the expected client id
- **THEN** the Speedy admin page shows the integration as healthy and displays the verified client id without showing the password

#### Scenario: Client id mismatch
- **WHEN** the Client Service returns a client id different from configured `speedy_client_id`
- **THEN** the Speedy admin page shows a configuration warning explaining that shipment sender identity may be wrong

#### Scenario: Missing credentials
- **WHEN** Speedy username, password, or numeric client id is missing
- **THEN** the Speedy admin page shows a blocked health state without attempting shipment creation

### Requirement: Phase 1 Speedy order fulfillment queues
The Speedy admin page SHALL list Speedy orders that need operational attention, including confirmed Speedy orders ready to ship and shipped Speedy orders with tracking numbers. The queues SHALL link back to admin order detail and SHALL provide order-level actions that respect existing state transitions.

#### Scenario: Ready-to-ship queue
- **WHEN** a confirmed order has `delivery_courier='speedy'` and no tracking number
- **THEN** the Speedy admin page lists it in a ready-to-ship queue with a create waybill action

#### Scenario: Shipped queue
- **WHEN** a shipped order has `tracking_carrier='speedy'`
- **THEN** the Speedy admin page lists it in a shipped queue with print label, refresh tracking, shipment info, and cancel availability indicators

### Requirement: Phase 1 Speedy shipment actions
The Speedy admin page SHALL expose actions for creating or reusing a waybill through the existing `confirmed -> shipped` flow, printing labels, refreshing tracking, looking up shipment information, searching by local order reference, and canceling a shipment when Speedy and local state allow cancellation.

#### Scenario: Create waybill from Speedy page
- **WHEN** an admin creates a waybill for a confirmed Speedy order without tracking
- **THEN** the system uses the existing shipped transition, persists the returned tracking number, and leaves the order unshipped if Speedy rejects the request

#### Scenario: Print existing label
- **WHEN** an admin prints a label for a Speedy order with a tracking number
- **THEN** the system streams the Speedy PDF label from the official Print Service

#### Scenario: Refresh tracking without changing order state
- **WHEN** an admin refreshes Speedy tracking from the Speedy page
- **THEN** the system updates display-only courier status and does not change order status, payment status, refund status, or stock

#### Scenario: Guarded cancellation
- **WHEN** an admin cancels a Speedy shipment that is locally not delivered and Speedy accepts cancellation
- **THEN** the system records the cancellation event and clears or marks local shipment metadata according to the cancellation policy

#### Scenario: Cancellation rejected by Speedy
- **WHEN** Speedy rejects a shipment cancellation because the shipment is already picked up, closed, or inaccessible
- **THEN** the system leaves local shipment metadata unchanged and shows an admin-safe error

### Requirement: Phase 2 Speedy pickup workflow
The Speedy admin page SHALL support requesting pickup terms and creating pickup requests for eligible Speedy shipments. Pickup requests SHALL be explicit admin actions and SHALL NOT run automatically during checkout or order confirmation.

#### Scenario: Show pickup terms
- **WHEN** an admin requests pickup terms for eligible Speedy shipments
- **THEN** the system calls the official Pickup Terms endpoint and displays available cutoff times or an actionable error

#### Scenario: Request pickup
- **WHEN** an admin chooses a pickup time and eligible shipment scope
- **THEN** the system calls the official Pickup endpoint, records returned pickup orders, and shows the pickup confirmation

### Requirement: Speedy audit and diagnostics
The Speedy admin page SHALL show recent Speedy operation history with action, status, order id, tracking number, timestamp, and redacted error details. Stored audit data SHALL never contain Speedy passwords.

#### Scenario: Successful operation recorded
- **WHEN** a Speedy shipment action succeeds from the Speedy page or order page
- **THEN** an audit entry is available on the Speedy admin page

#### Scenario: Failed operation recorded safely
- **WHEN** a Speedy API operation fails
- **THEN** the Speedy admin page shows the categorized failure without exposing credentials or raw secret-bearing payloads
