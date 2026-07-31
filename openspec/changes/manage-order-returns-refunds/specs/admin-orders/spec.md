## ADDED Requirements

### Requirement: Admin order detail includes return and refund context
The system SHALL include return cases, refund records, courier claim fields, COD settlement status, payment review status, and relevant audit events in admin order detail responses.

#### Scenario: Admin views order with active return case
- **WHEN** an authenticated admin retrieves an order with an active return case
- **THEN** the response includes the return reason, return status, restock decision, refund amount, courier fees, claim fields, and return timestamps

#### Scenario: Admin views order with refund records
- **WHEN** an authenticated admin retrieves a card order with refund attempts
- **THEN** the response includes refund amount, provider, provider refund ID, refund status, and failure reason when present

### Requirement: Admin can filter review queues
The system SHALL allow admins to filter orders needing operational review, including abandoned card payments, uncollected/refused shipments, refund pending, return inspection pending, courier claim follow-up, and COD settlement pending.

#### Scenario: Admin filters abandoned card payments
- **WHEN** an authenticated admin requests the abandoned-payment review filter
- **THEN** the response lists card orders that require callback and have not been confirmed for shipment

#### Scenario: Admin filters pending return inspections
- **WHEN** an authenticated admin requests the return-inspection filter
- **THEN** the response lists returned orders whose return case has no final restock decision

### Requirement: Admin can manage return cases
The system SHALL expose admin actions to mark return in transit, mark uncollected, mark refused delivery, receive return, inspect return, close return case, and record notes. Each action SHALL require admin authentication and write an audit event.

#### Scenario: Admin marks order uncollected
- **WHEN** an authenticated admin marks a shipped order as uncollected
- **THEN** the system creates or updates a return case with reason `not_picked_up`, sets order status to `return_in_transit`, and writes an audit event

#### Scenario: Admin receives return
- **WHEN** an authenticated admin receives a returned parcel
- **THEN** the system records the receive action, stores `received_at`, and keeps stock unchanged until inspection

#### Scenario: Non-admin cannot manage return cases
- **WHEN** a non-admin request attempts a return action
- **THEN** the API returns HTTP 403 and no return data changes

### Requirement: Admin can record courier fees and manual claims
The system SHALL allow admins to record courier return fees and manual courier claim data for lost or damaged shipments. Claim data SHALL be stored as recordkeeping only and MUST NOT require courier API integration.

#### Scenario: Admin records damage claim
- **WHEN** an authenticated admin records courier claim ID, claim status, claim amount, and notes for a damaged shipment
- **THEN** the system stores those fields on the return case and writes an audit event

#### Scenario: Admin records courier return fee
- **WHEN** an authenticated admin enters a return courier fee for an uncollected order
- **THEN** the fee is stored for accounting reconciliation

### Requirement: Admin can issue refunds from order detail
The system SHALL allow admins to issue full or partial refunds for eligible paid card orders from the admin order detail. The action SHALL validate payment method, paid status, Stripe PaymentIntent, refundable amount, and idempotency before contacting Stripe.

#### Scenario: Eligible full refund action succeeds
- **WHEN** an authenticated admin issues a full refund for an eligible paid card order
- **THEN** the system creates a Stripe refund, records the refund, and shows payment status `refund_pending`

#### Scenario: Ineligible COD refund action is rejected
- **WHEN** an authenticated admin attempts a Stripe refund on a COD order
- **THEN** the API rejects the action and does not call Stripe

### Requirement: Admin can handle abandoned card payment callback
The system SHALL allow admins to record callback outcome for abandoned card payments. Admins SHALL be able to convert the order to payment on delivery only after customer confirmation.

#### Scenario: Admin converts abandoned card order to payment on delivery
- **WHEN** an admin records that the customer confirmed an abandoned card order by phone
- **THEN** the system changes the order to payment on delivery, sets payment status `cod_pending`, records the original card attempt for audit, and allows normal confirmation/shipping workflow

#### Scenario: Abandoned card order cannot ship before callback confirmation
- **WHEN** an admin attempts to ship an abandoned card order still in payment review
- **THEN** the API rejects the transition and explains that admin callback confirmation is required

### Requirement: Admin can record COD settlement
The system SHALL allow admins to record COD settlement amount, date, courier reference, and notes for delivered COD orders.

#### Scenario: Admin records COD payout
- **WHEN** an authenticated admin records a courier COD payout for a delivered COD order
- **THEN** the system stores the settlement details and marks the order settled for COD reconciliation

#### Scenario: COD settlement amount mismatch is visible
- **WHEN** the recorded COD settlement amount differs from the order amount
- **THEN** the system stores the settlement and flags the order for accounting review
