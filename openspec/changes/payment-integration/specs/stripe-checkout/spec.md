## ADDED Requirements

### Requirement: Card orders create a Stripe Checkout Session
The system SHALL, after atomically creating a card order (stock decremented, order in DB with `payment_status='pending'`), create a Stripe Checkout Session using the server-calculated `order.total_cents` as the authoritative amount. The response for card orders SHALL include `stripe_checkout_url` for the frontend to redirect the customer. The Stripe session amount SHALL always be derived from `order.total_cents` in the database — never from a client-provided value.

#### Scenario: Card checkout returns Stripe redirect URL
- **WHEN** a customer places an order with `payment_method='card'`
- **THEN** the API returns HTTP 201 with the order fields plus `stripe_checkout_url` pointing to Stripe's hosted checkout page

#### Scenario: Stripe session uses server-calculated total
- **WHEN** a card order is created with `total_cents=4500`
- **THEN** the Stripe Checkout Session is created for exactly 4500 cents — no client-supplied amount is accepted

#### Scenario: Stripe API failure after order creation
- **WHEN** the order is committed to the DB but the Stripe API call fails
- **THEN** the order exists with `payment_status='pending'` and no `stripe_checkout_session_id`; the customer can retry via `POST /v1/orders/{id}/stripe-session`

### Requirement: Stripe webhook updates payment_status idempotently
The system SHALL expose `POST /v1/webhooks/stripe` that verifies the `Stripe-Signature` header, deduplicates events via the `stripe_events` table, and dispatches on event type. `checkout.session.completed` SHALL set `payment_status='paid'` and `stripe_payment_intent_id` on the order. `checkout.session.expired` SHALL set `payment_status='failed'`. All other event types SHALL be logged and return 200. The endpoint SHALL always return 200 for valid signatures, including already-processed events.

#### Scenario: Payment succeeded webhook marks order paid
- **WHEN** Stripe sends `checkout.session.completed` for order X
- **THEN** `payment_status` is set to `'paid'`, `stripe_payment_intent_id` is stored, and the webhook returns 200

#### Scenario: Duplicate webhook delivery is idempotent
- **WHEN** Stripe delivers `checkout.session.completed` for the same event twice
- **THEN** the second delivery is recognised via `stripe_events.event_id`, the order is not modified again, and 200 is returned

#### Scenario: Session expired webhook marks order failed
- **WHEN** Stripe sends `checkout.session.expired` for order X
- **THEN** `payment_status` is set to `'failed'` and 200 is returned; the order is not cancelled

#### Scenario: Invalid signature returns 400
- **WHEN** a request arrives at `POST /v1/webhooks/stripe` with an invalid or missing `Stripe-Signature`
- **THEN** the API returns HTTP 400 and no order data is modified

#### Scenario: Unknown event type is silently accepted
- **WHEN** Stripe sends an event type not handled by the system
- **THEN** the event is logged and 200 is returned with no order modification

### Requirement: Retry payment creates a new Stripe Checkout Session
The system SHALL expose `POST /v1/orders/{id}/stripe-session` that creates a fresh Stripe Checkout Session for an existing order with `payment_method='card'`. The caller's session SHALL own the order. The new `stripe_checkout_session_id` SHALL overwrite the previous value on the order. This is the recovery path for expired or failed sessions.

#### Scenario: Customer retries payment after session expiry
- **WHEN** a customer sends `POST /v1/orders/{id}/stripe-session` for their own order with `payment_status='failed'`
- **THEN** a new Stripe Checkout Session is created and `stripe_checkout_url` is returned

#### Scenario: Non-owner cannot create retry session
- **WHEN** a session that does not own order X sends `POST /v1/orders/{id}/stripe-session`
- **THEN** the API returns HTTP 404

#### Scenario: Already-paid order cannot create new session
- **WHEN** a customer sends `POST /v1/orders/{id}/stripe-session` for an order with `payment_status='paid'`
- **THEN** the API returns HTTP 409 indicating payment is already complete

### Requirement: Abandoned card orders are auto-cancelled after 24 hours
The system's background cleanup task SHALL cancel card orders where `payment_status IN ('pending', 'failed')` and `created_at < now - 24h`. Cancellation SHALL restore stock. This pass SHALL NOT affect COD or bank_transfer orders regardless of their payment_status.

#### Scenario: Abandoned card order cancelled after 24h
- **WHEN** a card order has `payment_status='pending'` and was created more than 24 hours ago
- **THEN** the cleanup task cancels the order and restores stock for all order items

#### Scenario: COD pending order is not auto-cancelled
- **WHEN** a COD order has `payment_status='cod_pending'` and is older than 24 hours
- **THEN** the cleanup task does NOT cancel it

#### Scenario: Bank transfer pending order is not auto-cancelled
- **WHEN** a bank_transfer order has `payment_status='pending'` and is older than 24 hours
- **THEN** the cleanup task does NOT cancel it
