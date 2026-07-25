## ADDED Requirements

### Requirement: Transactional mail sent from the authenticated root domain

The system SHALL send all transactional email from the root domain `theateliermarie.com` (using aliases such as `orders@`/`noreply@`), authenticated with DKIM and a bounce/return-path CNAME, and covered by DMARC. ZeptoMail authenticates the domain via a DKIM TXT record plus a bounce CNAME (`bounce-zem → cluster89.zeptomail.eu`) that carries SPF alignment; the existing Zoho SPF record SHALL be left unchanged (no second `v=spf1` record).

#### Scenario: From-address uses a root-domain alias

- **WHEN** the production email configuration is set
- **THEN** `EMAIL_FROM_ADDRESS` is an address on `theateliermarie.com` and `EMAIL_REPLY_TO` is the human `contacts@theateliermarie.com` mailbox

#### Scenario: DKIM alignment carries DMARC

- **WHEN** an order email is sent and DKIM-signed on `theateliermarie.com`
- **THEN** the message passes DMARC via DKIM alignment, independent of SPF, and the bounce CNAME provides SPF alignment on top

#### Scenario: Authentication records present

- **WHEN** the sending domain is verified in ZeptoMail
- **THEN** the ZeptoMail DKIM TXT (Default selector), the bounce CNAME, and a DMARC record are published and the domain shows verified

### Requirement: Open and click tracking disabled for transactional email

The system SHALL send transactional emails with open-tracking and click-tracking disabled, because tracking pixels and rewritten links degrade inbox placement and are unnecessary for transactional mail.

#### Scenario: Tracking off on send

- **WHEN** an order email is sent via the ZeptoMail provider
- **THEN** open-tracking and click-tracking are disabled on the request

### Requirement: No provider-level idempotency key (DB index is the guard)

ZeptoMail does not offer a send-level idempotency key. The system SHALL NOT depend on any provider-level dedup and SHALL rely solely on the DB-backed send claim plus the `order_emails` partial UNIQUE index (see the email-service capability) to suppress duplicate sends.

#### Scenario: Duplicate suppression is application-level only

- **WHEN** the same `(order_id, event)` send is attempted twice
- **THEN** the second send is prevented by the DB send claim or `order_emails` UNIQUE index (not by any provider idempotency header), and no provider idempotency key is attached to the request

### Requirement: Bounce and complaint webhooks suppress undeliverable recipients

The system SHALL expose a webhook endpoint (`POST /v1/webhooks/zeptomail`) that consumes ZeptoMail `hard_bounce`, `soft_bounce`, and `fbl_complaint` events and marks the affected recipient as undeliverable so no further mail is generated to it. The endpoint SHALL verify ZeptoMail's `producer-signature` HMAC-SHA256 (parts `ts`, `s`, `s-algorithm`) over the raw request body using the configured `zeptomail_webhook_auth_key`, reject stale timestamps to prevent replay, and use a constant-time comparison. It SHALL be public (signature-authenticated, not admin) and registered in `session_skip_paths`.

#### Scenario: Hard bounce marks recipient undeliverable

- **WHEN** a `hard_bounce` event is received with a valid signature
- **THEN** the recipient is recorded as undeliverable and subsequent order emails to that address are skipped and logged as "skipped_suppressed"

#### Scenario: Complaint marks recipient undeliverable

- **WHEN** a `fbl_complaint` event is received with a valid signature
- **THEN** the recipient is recorded as undeliverable

#### Scenario: Invalid signature rejected

- **WHEN** a webhook request arrives with a missing or invalid `producer-signature`
- **THEN** the endpoint returns 401/403 and does not mutate state

#### Scenario: Replay rejected

- **WHEN** a webhook request carries a valid signature but a `ts` timestamp outside the allowed tolerance (e.g. > 5 minutes old)
- **THEN** the endpoint rejects it and does not mutate state

#### Scenario: Signature computed over raw body

- **WHEN** the endpoint verifies a request
- **THEN** it verifies against the raw request bytes read before JSON parsing (not a re-serialized body)

#### Scenario: Duplicate bounce is idempotent

- **WHEN** the same bounce event is delivered twice (ZeptoMail redelivery)
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
