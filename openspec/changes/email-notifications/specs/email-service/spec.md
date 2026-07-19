## ADDED Requirements

### Requirement: Email service sends notifications on order state transitions

The system SHALL send a transactional email to the customer whenever their order transitions to a customer-facing state (placed/pending, shipped, delivered, cancelled). The `confirmed` transition SHALL NOT send a customer email. Emails are dispatched asynchronously via FastAPI BackgroundTasks and SHALL NOT block or fail the HTTP response.

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
- **THEN** the order status change succeeds normally and the failure is logged via structlog

#### Scenario: Email quota or credit exhausted

- **WHEN** the ZeptoMail provider returns a quota/credit-exhausted error
- **THEN** the system logs a warning and the order operation completes without sending the email

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

The system SHALL record each email send attempt in an append-only `order_emails` table capturing order_id, event, recipient, status (sent/failed/skipped), optional error, and timestamp. Recording the log row SHALL happen inside the background task and SHALL NOT propagate failures.

#### Scenario: Successful send logged

- **WHEN** a customer email is sent successfully
- **THEN** a row is written to `order_emails` with status "sent", the recipient, and the event

#### Scenario: Failed send logged

- **WHEN** the provider raises an error while sending
- **THEN** a row is written with status "failed" and the provider error message, and the order operation is unaffected

### Requirement: Duplicate emails are suppressed via a DB-level idempotency guard

The system SHALL NOT send the same customer email twice for the same order and event. A partial UNIQUE index on `order_emails(order_id, event) WHERE status='sent'` is the arbiter: the send path inserts the "sent" row first, and a uniqueness violation means the email was already sent and the send is skipped. This closes the check-then-send race across concurrent tasks and multiple workers.

#### Scenario: Concurrent sends of the same event produce one email

- **WHEN** two background tasks for the same (order_id, event) run concurrently (e.g. admin double-click or multiple workers)
- **THEN** exactly one email is sent; the losing insert hits the UNIQUE index and is logged with status "skipped_duplicate"

#### Scenario: Distinct events for the same order each send once

- **WHEN** an order progresses placed → shipped → delivered
- **THEN** three distinct emails are sent, one per event, each logged as "sent"
