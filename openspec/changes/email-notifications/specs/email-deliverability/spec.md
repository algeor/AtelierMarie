## ADDED Requirements

### Requirement: Transactional mail sent from an authenticated subdomain

The system SHALL send all transactional email from a dedicated sending subdomain (e.g. `send.ateliermarie.com`) authenticated with SPF, DKIM, and DMARC, rather than from the root domain.

#### Scenario: From-address uses the sending subdomain

- **WHEN** the production email configuration is set
- **THEN** `EMAIL_FROM_ADDRESS` is an address on the sending subdomain (not the bare root domain)

#### Scenario: Authentication records present

- **WHEN** the sending domain is verified in Resend
- **THEN** SPF (TXT + MX), DKIM (TXT), and DMARC records are published and the domain shows verified

### Requirement: Open and click tracking disabled for transactional email

The system SHALL send transactional emails with open-tracking and click-tracking disabled, because tracking pixels and rewritten links degrade inbox placement and are unnecessary for transactional mail.

#### Scenario: Tracking off on send

- **WHEN** an order email is sent via the Resend provider
- **THEN** open-tracking and click-tracking are disabled on the request

### Requirement: Idempotency key on every provider send

The system SHALL attach an idempotency key of the form `<event>/<order_id>` to each provider send, so retried sends within the provider's dedup window do not produce duplicate emails.

#### Scenario: Idempotency key format

- **WHEN** an "order shipped" email for order `AM-12ab34` is sent
- **THEN** the provider request carries idempotency key `order-shipped/AM-12ab34`

#### Scenario: Idempotency complements the order-email log

- **WHEN** the same event send is retried within the provider dedup window
- **THEN** no duplicate email is delivered (provider-level guard), independent of the `order_emails` table check (application-level guard)

### Requirement: Bounce and complaint webhooks suppress undeliverable recipients

The system SHALL expose a webhook endpoint (`POST /v1/webhooks/resend`) that consumes Resend `email.bounced`, `email.complained`, and `email.suppressed` events and marks the affected recipient as undeliverable so no further mail is generated to it. The endpoint SHALL verify the Resend (Svix) signature over the raw request body using a configured signing secret, reject stale timestamps to prevent replay, and use a constant-time comparison. It SHALL be public (signature-authenticated, not admin) and registered in `session_skip_paths`.

#### Scenario: Hard bounce marks recipient undeliverable

- **WHEN** a `email.bounced` event with a permanent bounce type is received with a valid signature
- **THEN** the recipient is recorded as undeliverable and subsequent order emails to that address are skipped and logged as "skipped_suppressed"

#### Scenario: Complaint marks recipient undeliverable

- **WHEN** a `email.complained` event is received with a valid signature
- **THEN** the recipient is recorded as undeliverable

#### Scenario: Invalid signature rejected

- **WHEN** a webhook request arrives with a missing or invalid Svix signature
- **THEN** the endpoint returns 401/403 and does not mutate state

#### Scenario: Replay rejected

- **WHEN** a webhook request carries a valid signature but a `svix-timestamp` outside the allowed tolerance (e.g. > 5 minutes old)
- **THEN** the endpoint rejects it and does not mutate state

#### Scenario: Signature computed over raw body

- **WHEN** the endpoint verifies a request
- **THEN** it verifies against the raw request bytes read before JSON parsing (not a re-serialized body)

#### Scenario: Duplicate bounce is idempotent

- **WHEN** the same bounce event is delivered twice (Resend redelivery)
- **THEN** the recipient's undeliverable state is unchanged and no error is raised

### Requirement: Email address validated at checkout

The system SHALL validate the customer email address format at checkout to minimize hard bounces to invalid addresses.

#### Scenario: Invalid email rejected at checkout

- **WHEN** a customer submits checkout with a malformed email address
- **THEN** checkout is rejected with a validation error before the order is created

### Requirement: Cyrillic subject headers are MIME-encoded

The system SHALL ensure non-ASCII (Cyrillic) email subjects and display names are transmitted as RFC 2047 encoded-words, and email bodies as UTF-8.

#### Scenario: Bulgarian subject round-trips

- **WHEN** an email with a Cyrillic subject line is sent
- **THEN** the transmitted `Subject` header is a valid RFC 2047 encoded-word (not raw bytes) and decodes back to the original text

### Requirement: No List-Unsubscribe on transactional mail

The system SHALL NOT attach a `List-Unsubscribe` header to transactional order emails, since these are contractually necessary messages, not marketing.

#### Scenario: Transactional email omits unsubscribe header

- **WHEN** any order email is sent
- **THEN** the message contains no `List-Unsubscribe` header
