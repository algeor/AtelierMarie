## ADDED Requirements

### Requirement: Email service sends notifications on order state transitions

The system SHALL send a transactional email to the customer whenever their order transitions to a new state (pending, confirmed, shipped, delivered, cancelled). Emails are dispatched asynchronously via FastAPI BackgroundTasks and SHALL NOT block or fail the HTTP response.

#### Scenario: Customer receives email after checkout

- **WHEN** a customer completes checkout (order transitions to "pending")
- **THEN** the system sends an "order placed" email to the customer's email address with order summary, item list, and total

#### Scenario: Customer receives email on order confirmation

- **WHEN** admin confirms an order (status → "confirmed")
- **THEN** the system sends an "order confirmed" email to the customer

#### Scenario: Customer receives email on order shipped

- **WHEN** admin marks order as shipped (status → "shipped")
- **THEN** the system sends an "order shipped" email containing tracking number, carrier name, and tracking URL

#### Scenario: Customer receives email on order delivered

- **WHEN** admin marks order as delivered (status → "delivered")
- **THEN** the system sends an "order delivered" email to the customer

#### Scenario: Customer receives email on order cancellation

- **WHEN** an order is cancelled (status → "cancelled")
- **THEN** the system sends an "order cancelled" email to the customer

#### Scenario: Email failure does not affect order operation

- **WHEN** the email provider is unavailable or returns an error
- **THEN** the order status change succeeds normally and the failure is logged via structlog

#### Scenario: Email rate limit hit

- **WHEN** the Resend daily quota (100 emails/day) is exceeded
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

#### Scenario: Resend provider in production

- **WHEN** `EMAIL_PROVIDER` is set to "resend" and `EMAIL_API_KEY` is configured
- **THEN** emails are sent via the Resend API using the configured from-address and API key

#### Scenario: Missing API key with Resend provider

- **WHEN** `EMAIL_PROVIDER` is "resend" but `EMAIL_API_KEY` is empty
- **THEN** the system logs a startup warning and all email sends are skipped with an error log

### Requirement: Email configuration via environment variables

The system SHALL read all email configuration from environment variables via Pydantic Settings.

#### Scenario: All email settings configurable

- **WHEN** the application starts
- **THEN** the following settings are available: `EMAIL_PROVIDER` (default "console"), `EMAIL_API_KEY`, `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` (default "Atelier Marie"), `EMAIL_REPLY_TO`, `ADMIN_NOTIFICATION_EMAIL`

#### Scenario: Default configuration works for development

- **WHEN** no email environment variables are set
- **THEN** the system uses the console provider and logs emails without sending
