## MODIFIED Requirements

### Requirement: Tracking is read-only and does not drive the order state machine
Tracking SHALL normalize Speedy's status code to a `courier_status` display enum in the system's own vocabulary (e.g. `in_transit`, `out_for_delivery`, `delivered`, `returned`, `failed`) and surface it read-only on the order. A track poll MUST NOT call the order state-transition path (`update_status`) and MUST NOT automatically change payment status, refund status, return status, or stock. When tracking indicates returned or failed delivery, the system SHALL create or update an admin review signal for the order.

#### Scenario: Track surfaces courier status without changing order state
- **WHEN** a track poll returns any Speedy status for an order
- **THEN** the order's displayed `courier_status` reflects the mapped value and the order's own `status` is unchanged

#### Scenario: Courier "delivered" does not auto-advance or auto-mark paid
- **WHEN** Speedy reports the shipment as delivered
- **THEN** the order remains in its current state until an admin confirms delivery through the guarded transition, and no COD payment is auto-marked by the track poll

#### Scenario: Courier-only states are shown and flagged for review
- **WHEN** Speedy reports a status with no order-state equivalent, such as returned to sender or delivery failed
- **THEN** the system displays the mapped `courier_status`, creates or updates an admin review signal, and does not coerce the order into `delivered`, `returned`, or `cancelled`

#### Scenario: Returned tracking does not refund or restock
- **WHEN** Speedy reports the shipment as returned
- **THEN** the system does not issue a refund, change payment status, or restore stock without an explicit admin action
