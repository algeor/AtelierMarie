## ADDED Requirements

### Requirement: Stripe Checkout creates payment sessions server-side
The system SHALL create Stripe Checkout Sessions only on the backend, using the
server-side order snapshot amount in EUR cents. The frontend SHALL NOT provide or
authoritatively control the payable amount. The Checkout Session SHALL be a
one-time payment and SHALL include only non-sensitive metadata.

#### Scenario: Card checkout returns Stripe URL
- **WHEN** a customer selects card payment and submits valid checkout details
- **THEN** the backend creates a local order/payment record, reserves stock, creates
  a Stripe Checkout Session, and returns the Stripe checkout URL
- **AND** the frontend redirects the customer to Stripe

#### Scenario: Frontend amount is ignored
- **WHEN** a checkout request includes a manipulated total amount
- **THEN** the backend computes the Stripe amount from the server-side order/cart
  snapshot and does not trust the frontend amount

#### Scenario: Sensitive metadata excluded
- **WHEN** the backend creates a Stripe Checkout Session
- **THEN** Stripe metadata includes only safe identifiers such as order id/order
  number and environment
- **AND** metadata does not include delivery address, phone, customer notes, or
  admin-only data

### Requirement: Card reservations expire after 15 minutes locally
The system SHALL reserve/decrement stock for card payment attempts for 15 minutes.
An expiry cleanup SHALL run every 1 minute and cancel expired unpaid card attempts,
restore stock, record a payment event, and attempt to expire the Stripe Checkout
Session.

#### Scenario: Expired unpaid card reservation restores stock
- **WHEN** a card payment order remains unpaid after `reserved_until`
- **THEN** cleanup marks the payment as cancelled, restores stock for all order
  items, records a payment event, and does not restore the cart

#### Scenario: Late Stripe success after local expiry requires review
- **WHEN** a verified Stripe success event arrives after local expiry restored stock
- **THEN** the system marks payment as `payment_review_required`, records an event,
  and alerts admin instead of automatically marking paid

### Requirement: Stripe payment retry is session-bound and token-bound
The system SHALL allow customers to retry card payment for the same unpaid reserved
order only while the reservation is valid. Retry SHALL require the same owning
session/user and a valid `payment_return_token`. Active unexpired Checkout Sessions
SHALL be reused for the same order.

#### Scenario: Valid retry reuses active session
- **WHEN** the owning session retries payment for an unpaid reserved order with a
  valid return token and active Checkout Session
- **THEN** the backend returns the existing Stripe Checkout URL rather than creating
  duplicate orders

#### Scenario: Retry from different session rejected
- **WHEN** a different session attempts to retry payment using the return token
- **THEN** the backend rejects the request and does not create a Stripe session

#### Scenario: Retry after expiry rejected
- **WHEN** a customer retries payment after the reservation expired
- **THEN** the backend rejects retry and does not create or reuse a Stripe session

### Requirement: Stripe webhooks are verified and idempotent
The system SHALL expose `POST /v1/webhooks/stripe` skipped by session middleware.
The endpoint SHALL verify Stripe signatures using the raw request body, reject
invalid signatures, process only allowlisted event types, and store Stripe event ids
with uniqueness for idempotency.

#### Scenario: Invalid signature rejected
- **WHEN** a webhook request has a missing or invalid Stripe signature
- **THEN** the API returns 401 or 400 and does not mutate payment state

#### Scenario: Duplicate event idempotent
- **WHEN** Stripe redelivers an already-processed event id
- **THEN** the backend does not duplicate payment events or repeat state mutations

#### Scenario: Checkout completed marks payment paid
- **WHEN** a valid `checkout.session.completed` event matches an active reserved
  order
- **THEN** payment status becomes `paid`, paid_at is set, and the customer order
  email is queued

#### Scenario: Refund event is audit-only
- **WHEN** a valid `charge.refunded` event is received in MVP
- **THEN** the backend records a payment event but does not mutate order/payment
  state

### Requirement: Payment events are append-only audit
The system SHALL append `payment_events` for Stripe webhooks, manual admin actions,
pay-on-delivery collection, expiry cleanup, and review-required transitions. Events
SHALL avoid storing raw webhook payloads or customer PII by default.

#### Scenario: Manual override records note
- **WHEN** an admin manually marks payment paid or collected
- **THEN** the backend requires an admin-only note and records a payment event with
  admin identity and request id

### Requirement: Payment rate limits protect checkout surfaces
The system SHALL enforce MVP payment rate limits: checkout creation 5 per 15
minutes per session and 20 per hour per IP; Stripe session creation 3 per order and
10 per hour per session; pay on delivery 2 per hour per session and 5 per day per
IP; payment status polling 60 per 5 minutes per session/IP. Signed Stripe webhooks
SHALL use signature verification and body-size caps rather than ordinary IP rate
limits.

#### Scenario: Pay-on-delivery rate limit exceeded
- **WHEN** a session exceeds the pay-on-delivery order limit
- **THEN** the backend rejects the request with a rate-limit error and does not
  create an order
