## MODIFIED Requirements

### Requirement: Email service sends notifications on order state transitions
The system SHALL send transactional emails on order events according to the following rules, which vary by payment_method:

- **COD orders:** queue `placed` email at order creation (no payment event follows).
- **Card orders:** queue `payment_pending` email at order creation; queue `placed` email when `payment_intent.succeeded` webhook fires (`payment_status → 'paid'`).
- **Bank transfer orders:** queue `payment_pending` email (including IBAN instructions) at order creation; queue `placed` email when admin marks payment received.
- **All methods:** `confirmed` transition sends no customer email. `shipped`, `delivered`, `cancelled` send customer emails as before.

The `confirmed` transition SHALL NOT send a customer email. Email dispatch SHALL NOT block or fail the HTTP response.

#### Scenario: COD order — placed email sent at checkout
- **WHEN** a customer completes checkout with `payment_method='cod'`
- **THEN** the `placed` email is queued immediately in the checkout transaction

#### Scenario: Card order — payment_pending email sent at checkout
- **WHEN** a customer completes checkout with `payment_method='card'`
- **THEN** the `payment_pending` email is queued (not `placed`); no misleading thank-you is sent before payment

#### Scenario: Card order — placed email sent on payment confirmed
- **WHEN** the `checkout.session.completed` webhook fires for a card order
- **THEN** the `placed` email is queued for the customer

#### Scenario: Bank transfer order — payment_pending email with IBAN sent at checkout
- **WHEN** a customer completes checkout with `payment_method='bank_transfer'`
- **THEN** the `payment_pending` email is queued; it includes IBAN, BIC, bank name, and payment reference

#### Scenario: Bank transfer order — placed email sent when admin marks paid
- **WHEN** an admin marks a bank_transfer order's payment as received
- **THEN** the `placed` email is queued for the customer

#### Scenario: Order confirmation does not email the customer
- **WHEN** admin confirms an order (status → "confirmed")
- **THEN** no customer email is sent

#### Scenario: Customer receives email on order shipped
- **WHEN** admin marks order as shipped (status → "shipped")
- **THEN** the system sends an "order shipped" email containing tracking number, carrier name, and tracking URL

#### Scenario: Customer receives email on order delivered
- **WHEN** admin marks order as delivered (status → "delivered")
- **THEN** the system sends an "order delivered" email to the customer

#### Scenario: Cancelled card order with payment — refund language shown
- **WHEN** a card order with `payment_status='paid'` is cancelled
- **THEN** the `cancelled` email includes refund language ("a refund is being processed")

#### Scenario: Cancelled COD order — no refund language
- **WHEN** a COD order is cancelled (payment_status='cod_pending', no money collected)
- **THEN** the `cancelled` email does NOT include refund language

#### Scenario: Cancelled card order without payment — no refund language
- **WHEN** a card order with `payment_status='pending'` or `'failed'` is cancelled
- **THEN** the `cancelled` email does NOT include refund language (no payment was taken)

#### Scenario: Email failure does not affect order operation
- **WHEN** the email provider is unavailable or returns an error
- **THEN** the order state change succeeds normally and the queued row remains for the sweeper to retry
