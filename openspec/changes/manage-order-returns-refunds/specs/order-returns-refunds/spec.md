## ADDED Requirements

### Requirement: Return cases are recorded separately from orders
The system SHALL store return and uncollected-order handling in return case records linked to the original order. A return case SHALL include reason, source, status, refund amount, courier return fee, manual courier claim fields, restock decision, timestamps, notes, and admin actor where available.

#### Scenario: Admin creates uncollected return case
- **WHEN** an admin marks a shipped courier-office order as not picked up
- **THEN** the system creates a return case with reason `not_picked_up`, source `admin`, status `return_in_transit`, and links it to the order

#### Scenario: Courier damage claim details are recorded manually
- **WHEN** an admin records a damaged-by-courier return with claim ID `CLM-123`, claim status `filed`, and claim amount 1500 cents
- **THEN** the return case stores the claim ID, claim status, claim amount, and admin notes without calling a courier claim API

### Requirement: Return lifecycle is admin controlled
The system SHALL allow admins to move return cases through return in transit, received, inspected, and closed states. The system MUST NOT automatically close a return case from courier tracking alone.

#### Scenario: Receive returned parcel
- **WHEN** an admin marks a return case as received
- **THEN** the system stores `received_at`, records an audit event, and keeps restock decision pending until inspection

#### Scenario: Courier status cannot close return case
- **WHEN** courier tracking reports `returned`
- **THEN** the system MAY create or update a review signal but SHALL NOT mark the return case received, inspected, or closed automatically

### Requirement: Returned stock is restored only after inspection
The system SHALL restore inventory for returned items only after an admin records a restock decision. The system SHALL support restock, do not restock, and partial restock decisions.

#### Scenario: Admin restocks received return
- **WHEN** an admin inspects a received return and chooses restock for 2 units of product A
- **THEN** product A stock increases by 2 and a stock adjustment reason is recorded

#### Scenario: Damaged return is not restocked
- **WHEN** an admin inspects a damaged return and chooses do not restock
- **THEN** product stock remains unchanged and the decision is recorded on the return case

### Requirement: Stripe refunds are issued and tracked
The system SHALL allow admins to issue full or partial Stripe refunds for paid card orders. The system SHALL create the refund through Stripe, persist a refund record with provider refund ID and idempotency key, and set payment status to `refund_pending` until provider confirmation.

#### Scenario: Admin issues full Stripe refund
- **WHEN** an admin issues a full refund for a paid card order with a Stripe PaymentIntent
- **THEN** the system calls Stripe refund creation, stores the Stripe refund ID and amount, and marks payment status `refund_pending`

#### Scenario: Stripe confirms full refund
- **WHEN** Stripe sends a refund succeeded event covering the full paid amount
- **THEN** the system marks the refund record succeeded and sets the order payment status to `refunded`

#### Scenario: Stripe confirms partial refund
- **WHEN** Stripe sends a refund succeeded event covering less than the paid amount
- **THEN** the system marks the refund record succeeded and sets the order payment status to `partially_refunded`

### Requirement: Refunds are idempotent and bounded
The system SHALL prevent duplicate or excessive refunds. Total succeeded and pending refund amounts for an order MUST NOT exceed the amount paid.

#### Scenario: Duplicate refund request uses idempotency
- **WHEN** an admin repeats the same refund action with the same idempotency key
- **THEN** the system returns the existing refund record instead of creating a second Stripe refund

#### Scenario: Excess refund is rejected
- **WHEN** an admin attempts to refund more than the remaining refundable amount
- **THEN** the system rejects the request and does not call Stripe

### Requirement: Refund failures require admin review
The system SHALL keep payment status reviewable when a provider refund fails. A failed refund SHALL NOT be treated as refunded.

#### Scenario: Stripe refund fails
- **WHEN** Stripe reports a refund failure
- **THEN** the system marks the refund record failed, records the failure reason, and leaves the order in an admin-reviewable payment state

### Requirement: COD settlement records are tracked
The system SHALL track COD collection and settlement separately from delivery. Delivered COD orders SHALL be distinguishable from COD payouts that have or have not been received by the merchant.

#### Scenario: COD delivered but not settled
- **WHEN** a COD order is marked delivered and courier settlement has not been recorded
- **THEN** the system shows the order as requiring COD settlement reconciliation

#### Scenario: Admin records COD settlement
- **WHEN** an admin records courier COD settlement amount, date, and reference
- **THEN** the system stores the settlement details and clears the settlement review flag for that order

### Requirement: Card disputes are distinct from refunds
The system SHALL represent Stripe disputes or chargebacks separately from refunds. Dispute records SHALL include Stripe dispute ID, status, evidence deadline where available, and outcome.

#### Scenario: Stripe dispute opened
- **WHEN** Stripe sends a dispute opened event for a paid order
- **THEN** the system records the dispute and sets payment status `dispute_open`

#### Scenario: Stripe dispute resolved
- **WHEN** Stripe sends a dispute won or lost event
- **THEN** the system records the outcome and sets payment status to `dispute_won` or `dispute_lost`

### Requirement: Exchange workflow is excluded
The system SHALL NOT implement a combined exchange workflow in this change. A return and a new purchase SHALL be separate processes.

#### Scenario: Customer wants different item after return
- **WHEN** an admin processes a return and the customer wants another item
- **THEN** the return is handled independently and the customer must place a separate new order for the new item
