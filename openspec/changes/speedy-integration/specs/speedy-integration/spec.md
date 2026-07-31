## ADDED Requirements

### Requirement: Speedy sender identity is explicit and verified
Every Speedy `calculate` and `shipment` request SHALL include a numeric `sender.clientId` sourced from a dedicated config field (`speedy_client_id`), distinct from the API login (`speedy_api_username`). The `clientId` is Speedy's registered client/contract object identifier — NOT an office id, and NOT reused from any office-slug field.

The pre-existing `speedy_sender_office_id` field is renamed to `speedy_client_id` because it was threaded into `sender.clientId` while being named (and populated with) an office slug — a naming/type mismatch that let an empty, non-numeric value reach Speedy on every call.

#### Scenario: Sender clientId present and numeric
- **WHEN** a Speedy calculate or shipment request is assembled with a configured numeric `speedy_client_id`
- **THEN** the outgoing payload carries `sender.clientId` set to that numeric value

#### Scenario: Missing or non-numeric sender clientId is diagnosable
- **WHEN** `speedy_client_id` is empty or not numeric at the time a Speedy request is assembled
- **THEN** the system logs a distinct `speedy_sender_client_id_invalid` warning (not a generic transport-failure/fallback warning) so a misconfigured sender is distinguishable from a Speedy outage

#### Scenario: Live door quote proves sender identity
- **WHEN** a door-mode calculate is issued against the demo account with the configured `speedy_client_id`
- **THEN** the returned quote carries `price_source="live"` (not the flat fallback), confirming Speedy accepted the sender identity end-to-end

### Requirement: Speedy payload contract is asserted independent of transport
Unit tests SHALL assert the shape of the outgoing Speedy request payload (that `sender.clientId` is present and numeric-looking, and that `pickupOfficeId` in office mode is numeric) rather than only asserting the normalized result. A mocked HTTP client that returns a canned price MUST NOT be able to hide a payload Speedy would reject.

#### Scenario: Payload assembly test catches a bad sender
- **WHEN** the Speedy client assembles a calculate payload with an empty or slug `clientId`
- **THEN** a unit test detects the invalid `sender.clientId` from the assembled payload, without depending on a live Speedy response

### Requirement: Waybill created on the ship transition, never leaving an order shipped without one
The system SHALL create a Speedy waybill on the `confirmed → shipped` transition (not on `pending → confirmed`), reusing the existing `update_status` shipped-path. Waybill creation SHALL run only when the order's courier is Speedy AND no tracking number was supplied; the returned parcel/shipment id becomes the order's `tracking_number`.

Confirmation MUST NOT depend on the courier — a Speedy outage may block shipping an order but never confirming it.

#### Scenario: Automatic waybill on ship
- **WHEN** an admin ships a Speedy order that has no tracking number
- **THEN** the system creates the waybill, stores the returned tracking number, and sets status to `shipped` in a single transaction

#### Scenario: Shipment creation failure does not advance state
- **WHEN** Speedy waybill creation fails during the ship transition
- **THEN** the transaction does not commit, the order remains `confirmed` (never `shipped` without a waybill), and the mapped Speedy error is surfaced to the admin (no silent fallback)

#### Scenario: Idempotent re-ship
- **WHEN** the ship transition runs for an order that already has a tracking number
- **THEN** the system skips the courier call and does not create a second waybill

#### Scenario: Manual tracking entry preserved
- **WHEN** an admin supplies a tracking number by hand (e.g. Speedy unavailable, or a non-courier shipment)
- **THEN** the system skips automatic waybill creation and ships using the supplied number

### Requirement: Tracking is read-only and does not drive the order state machine
Tracking SHALL normalize Speedy's status code to a `courier_status` display enum in the system's own vocabulary (e.g. `in_transit`, `out_for_delivery`, `delivered`, `returned`, `failed`) and surface it read-only on the order. A track poll MUST NOT call the order state-transition path (`update_status`) — the order state machine (`pending/confirmed/shipped/delivered/cancelled`) stays admin-driven.

#### Scenario: Track surfaces courier status without changing order state
- **WHEN** a track poll returns any Speedy status for an order
- **THEN** the order's displayed `courier_status` reflects the mapped value and the order's own `status` is unchanged

#### Scenario: Courier "delivered" does not auto-advance or auto-mark paid
- **WHEN** Speedy reports the shipment as delivered
- **THEN** the order remains in its current state until an admin confirms delivery through the guarded transition, and no COD payment is auto-marked by the track poll

#### Scenario: Courier-only states are shown, not forced into order states
- **WHEN** Speedy reports a status with no order-state equivalent (e.g. returned to sender, delivery failed)
- **THEN** the system displays the mapped `courier_status` and does not coerce the order into `delivered` or `cancelled`


