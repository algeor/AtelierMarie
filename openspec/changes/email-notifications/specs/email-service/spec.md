## ADDED Requirements

### Requirement: Email service sends notifications on order state transitions

The system SHALL send a transactional email to the customer whenever their order transitions to a customer-facing state (placed/pending, shipped, delivered, cancelled). The `confirmed` transition SHALL NOT send a customer email. Email dispatch SHALL NOT block or fail the HTTP response: the intent to send is persisted durably (a `queued` row in the same transaction as the order) and delivered asynchronously by a background sweeper, not by FastAPI BackgroundTasks. See the durable-delivery requirement below.

#### Scenario: Customer receives email after checkout

- **WHEN** a customer completes checkout (order transitions to "pending")
- **THEN** the system sends an "order placed" email to the customer's email address with order summary, item list, and total

#### Scenario: Order confirmation does not email the customer

- **WHEN** admin confirms an order (status → "confirmed")
- **THEN** no customer email is sent (pending→confirmed is an internal step; the next customer email is on ship)

#### Scenario: Customer receives email on order shipped

- **WHEN** admin marks order as shipped (status → "shipped")
- **THEN** the system sends an "order shipped" email containing tracking number, carrier name, and tracking URL

#### Scenario: Customer receives email on order delivered

- **WHEN** admin marks order as delivered (status → "delivered")
- **THEN** the system sends an "order delivered" email to the customer

#### Scenario: Customer receives email on order cancellation

- **WHEN** an order is cancelled (status → "cancelled")
- **THEN** the system sends an "order cancelled" email to the customer that states a refund is being processed

#### Scenario: Email failure does not affect order operation

- **WHEN** the email provider is unavailable or returns an error
- **THEN** the order status change succeeds normally, the attempt is logged via structlog, and the `queued`/`failed` row remains for the sweeper to retry (the email is delayed, not lost)

#### Scenario: Email quota or credit exhausted

- **WHEN** the ZeptoMail provider returns a quota/credit-exhausted error
- **THEN** the order operation completes without sending, the attempt is logged, and after MAX retry attempts the row is marked `failed_permanent` with an admin alert (retrying cannot fix an exhausted quota — a human must top up)

### Requirement: Admin receives notification on new order

The system SHALL send a notification email to the configured admin email address whenever a new order is placed.

#### Scenario: Owner receives new order alert

- **WHEN** a customer completes checkout
- **THEN** the system sends an email to `ADMIN_NOTIFICATION_EMAIL` containing order ID, total, customer name, customer email, item list, and a link to the admin order detail page

#### Scenario: No admin email configured

- **WHEN** a new order is placed and `ADMIN_NOTIFICATION_EMAIL` is empty
- **THEN** no admin notification is sent and no error is raised

### Requirement: Email provider abstraction supports multiple backends

The system SHALL use a provider protocol (`EmailProvider`) that allows swapping email backends without changing service logic.

#### Scenario: Console provider in development

- **WHEN** `EMAIL_PROVIDER` is set to "console"
- **THEN** all emails are logged to stdout with full context (recipient, subject, body) and no network call is made

#### Scenario: ZeptoMail provider in production

- **WHEN** `EMAIL_PROVIDER` is set to "zeptomail" and `EMAIL_API_KEY` is configured
- **THEN** emails are sent via the ZeptoMail HTTP API using the configured from-address and Send Mail token

#### Scenario: Missing API key with ZeptoMail provider

- **WHEN** `EMAIL_PROVIDER` is "zeptomail" but `EMAIL_API_KEY` is empty
- **THEN** the system logs a startup warning and all email sends are skipped with an error log

### Requirement: Email configuration via environment variables

The system SHALL read all email configuration from environment variables via Pydantic Settings.

#### Scenario: All email settings configurable

- **WHEN** the application starts
- **THEN** the following settings are available: `EMAIL_PROVIDER` (default "console"), `EMAIL_API_KEY`, `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` (default "Atelier Marie"), `EMAIL_REPLY_TO`, `ADMIN_NOTIFICATION_EMAIL`

#### Scenario: Default configuration works for development

- **WHEN** no email environment variables are set
- **THEN** the system uses the console provider and logs emails without sending

### Requirement: Email language follows the order's snapshotted locale

The system SHALL determine the language of every customer email from the locale stored on the order row, not from the acting session. This ensures admin-triggered emails (shipped, delivered, cancelled) are sent in the customer's language rather than the admin's.

#### Scenario: Admin-triggered email uses customer locale

- **WHEN** a customer placed an order with locale "bg" and an admin (locale "en") marks it shipped
- **THEN** the "order shipped" email is rendered from the Bulgarian template, using `orders.locale`

#### Scenario: Locale read from order after session expiry

- **WHEN** an order is shipped after the customer's original session has expired
- **THEN** the email language is still determined correctly from `orders.locale` with no session lookup

### Requirement: Every send attempt is recorded in an order-email log

The system SHALL record each email send attempt in an append-only `order_emails` table capturing order_id, event, recipient, status (queued/sent/failed/failed_permanent/skipped_duplicate/skipped_in_flight/skipped_suppressed), attempt count, optional error or skip reason, and timestamp. Updating the log row SHALL happen inside the sweeper's send path and SHALL NOT propagate failures.

#### Scenario: Successful send logged

- **WHEN** a customer email is sent successfully
- **THEN** the `order_emails` row reaches status "sent" with the recipient and the event

#### Scenario: Failed send logged

- **WHEN** the provider raises a transient error while sending
- **THEN** the row is recorded as "failed" with the provider error message, its attempt count incremented and a backoff time set, and the order operation is unaffected

#### Scenario: Permanently failed send is terminal

- **WHEN** the provider returns a permanent error (e.g. malformed request) or the row reaches the maximum retry attempts
- **THEN** the row is marked "failed_permanent", an admin alert is emitted, and the sweeper stops retrying it

### Requirement: Duplicate emails are suppressed via a DB-level idempotency guard

The system SHALL suppress duplicate customer emails for the same order and event with a DB-backed send claim keyed by `(order_id, event)`. The send path SHALL acquire an in-flight claim before calling the provider; if a successful send is already recorded, the send is skipped as `skipped_duplicate`, and if another worker's sweeper holds an unexpired in-flight claim, the send is skipped as `skipped_in_flight`. The system SHALL record the send as "sent" only after the provider call succeeds. If the provider raises an error, the system SHALL record a "failed" attempt and leave the claim retryable rather than marking the email as sent. A partial UNIQUE index on `order_emails(order_id, event) WHERE status='sent'` remains the audit invariant that at most one successful send is recorded. This guard is load-bearing because prod runs 2 uvicorn workers, each running its own sweeper over the same table.

#### Scenario: Concurrent sends of the same event produce one email

- **WHEN** two sweepers (the 2 prod workers) pick up the same `(order_id, event)` row on the same tick
- **THEN** at most one acquires the in-flight claim and calls the provider; the loser is logged with status "skipped_in_flight" or, if the winner already completed, "skipped_duplicate"

#### Scenario: Failed send remains retryable

- **WHEN** the provider raises an error after the task acquires the in-flight claim
- **THEN** a "failed" row is written, no "sent" row is written, and a later retry can acquire the claim and attempt the send again

#### Scenario: Distinct events for the same order each send once

- **WHEN** an order progresses placed → shipped → delivered
- **THEN** three distinct emails are sent, one per event, each logged as "sent"

### Requirement: Email delivery is durable (no lost handoff)

The system SHALL guarantee that every email it owes is delivered to the provider at least once, surviving process restarts, deploys, and provider outages. The intent to send SHALL be written as a `queued` `order_emails` row in the same database transaction as the order state change, and a background sweeper (one per worker, ~15s interval) SHALL drive each row to a terminal state (`sent` or `failed_permanent`) with bounded retry and exponential backoff. This is at-least-once delivery: a rare duplicate (provider accepted but the process died before recording "sent") is preferred over a lost email. This guarantee covers handoff to the provider only; an undeliverable address (hard bounce/complaint) is routed to suppression, not retried.

#### Scenario: Email survives a crash before sending

- **WHEN** the process restarts (deploy/crash/OOM) after an order commits but before its email is sent
- **THEN** the `queued` row persists (it was committed with the order) and the sweeper sends it after restart — the email is not lost

#### Scenario: Provider outage delays but does not lose the email

- **WHEN** the provider is down for several sweeper ticks and then recovers
- **THEN** the row is retried with backoff across ticks and delivered once the provider returns, with exactly one "sent" recorded (no duplicate from the retries)

#### Scenario: Admin alert is not the sole notification channel

- **WHEN** the provider is down at checkout so the `admin_new_order` email cannot be sent immediately
- **THEN** the order is still visible in the admin dashboard (a durable DB row, independent of the provider) and the queued admin email is delivered by the sweeper once the provider recovers
