## MODIFIED Requirements

### Requirement: Admin order list is payment-aware
Admin order list SHALL show public order number, payment method, payment status,
and payment status filters/sections for pending, failed, cancelled, and review
required payments. Admin labels SHALL be operational.

#### Scenario: Admin sees pending Stripe payment
- **WHEN** admin lists orders containing an unpaid card order
- **THEN** the row shows payment label `Stripe pending`

#### Scenario: Admin filters review-required payments
- **WHEN** admin filters for review-required payments
- **THEN** only orders with `payment_status = payment_review_required` are shown

### Requirement: Admin order detail includes payment timeline
Admin order detail SHALL include an admin-only payment timeline sourced from
`payment_events`, including webhook events, expiry cleanup, manual overrides,
pay-on-delivery collection, and review-required transitions.

#### Scenario: Payment timeline shows webhook event
- **WHEN** admin opens an order that has a Stripe webhook event
- **THEN** the timeline shows event type, timestamp, processing status, and safe
  Stripe identifiers without customer PII

### Requirement: Admin manual payment actions require notes
The system SHALL allow admins to mark payment paid, mark pay-on-delivery collected,
cancel/refund manually, or move payment to review according to allowed actions.
Every manual override SHALL require an admin-only note and write a payment event.

#### Scenario: Mark COD collected
- **WHEN** admin marks a pay-on-delivery payment collected with a note
- **THEN** payment status becomes `collected`, collected_at is set, and a payment
  event records the admin note

#### Scenario: Missing note rejected
- **WHEN** admin attempts a manual payment override without a note
- **THEN** the backend rejects the request and does not mutate payment state

### Requirement: Review-required alerts are immediate
When payment enters `payment_review_required`, the system SHALL create an in-app
admin alert and send an immediate admin email containing order number, reason,
Stripe Checkout Session ID, Stripe PaymentIntent ID when known, and admin order
link. The email SHALL NOT include customer PII.

#### Scenario: Late Stripe success alerts admin
- **WHEN** a late Stripe success after reservation expiry marks payment review
  required
- **THEN** admin receives an in-app alert and email with safe payment identifiers
