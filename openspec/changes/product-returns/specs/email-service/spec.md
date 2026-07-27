## ADDED Requirements

### Requirement: Return lifecycle emails use the durable outbox
Return notifications SHALL be queued as `order_emails` rows and sent by the existing
sweeper — no separate send path. The event vocabulary SHALL be extended with three
customer events (`return_approved`, `return_rejected`, `return_refunded`) and one admin
event (`admin_return_requested`). Refund emails SHALL be queued only after the refund is
confirmed (Stripe webhook) or recorded (manual), never on a refund attempt.

#### Scenario: Approval queues a customer email
- **WHEN** an admin approves a return
- **THEN** a `return_approved` row is queued in `order_emails` for the order's customer email

#### Scenario: Admin alerted on new return request
- **WHEN** a customer submits a return request
- **THEN** an `admin_return_requested` row is queued to the admin notification address

#### Scenario: Refund email waits for confirmation
- **WHEN** a card refund is attempted but not yet confirmed by webhook
- **THEN** no `return_refunded` email is queued until the confirming webhook is processed
