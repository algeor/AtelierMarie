## ADDED Requirements

### Requirement: Admin finance hub access
The system SHALL provide an admin-only Accounting & Finance Hub at `/admin/accounting`. The hub SHALL require existing admin authentication and SHALL deny unauthenticated or non-admin users using the existing admin access behavior.

#### Scenario: Admin opens finance hub
- **WHEN** an authenticated admin navigates to `/admin/accounting`
- **THEN** the system renders the Accounting & Finance Hub with period controls, summary totals, exception status, export status, and navigation to ledgers/settings

#### Scenario: Non-admin is denied
- **WHEN** a non-admin user navigates to `/admin/accounting`
- **THEN** the system denies access using the existing admin protection behavior

### Requirement: Finance period lifecycle
The system SHALL manage accounting periods with explicit lifecycle states: `open`, `review`, `closed`, `exported`, `accepted`, and `reopened`. A period SHALL have a start date, end date, currency, status, created timestamp, updated timestamp, and actor/reason audit events for every status change.

#### Scenario: Admin creates a monthly period
- **WHEN** an admin creates a finance period for 2026-08-01 through 2026-08-31 in EUR
- **THEN** the system creates the period with status `open` and records a finance audit event with the admin actor

#### Scenario: Admin moves period to review
- **WHEN** an admin starts month-end review for an open period
- **THEN** the period status becomes `review` and the system computes current summary totals and review exceptions for that period

#### Scenario: Accepted period cannot be edited silently
- **WHEN** a period has status `accepted` and an admin needs to correct it
- **THEN** the system requires a reopen action with a reason and records the period as `reopened` before any new export version can be created

### Requirement: Finance summary totals
The system SHALL show period summary totals for gross sales, discounts, returns/sales reversals, net sales, shipping charged, VAT/tax amount, total customer payments, Stripe fees, courier/COD fees, net provider payouts, COD receivable, refunds pending, and review-required item count. Totals SHALL be calculated from accounting ledgers, not from a single order total field.

#### Scenario: Summary separates revenue and cash
- **WHEN** a period contains card orders paid in August but paid out by Stripe in September
- **THEN** the sales totals appear in the August sales view while the Stripe payout amount is shown by its payout effective/arrival date and not merged into August sales revenue

#### Scenario: Summary includes COD receivable
- **WHEN** a delivered payment-on-delivery order has no matching COD settlement record
- **THEN** the period summary includes the order amount in COD receivable and increments review-required item count

### Requirement: Accounting exception queue
The system SHALL compute review exceptions for accounting risks including missing seller legal profile, missing VAT/fiscal classification, missing document reference when required, paid order without payment evidence, provider payment without order match, Stripe payout mismatch, delivered COD order without settlement, COD amount mismatch, refund without document reference when required, duplicate provider ID, and rounding differences above configured tolerance.

#### Scenario: Missing fiscal document blocks close
- **WHEN** a period contains an order that requires a fiscal or invoice document reference but none is recorded
- **THEN** the exception queue shows a blocking exception linked to the order and the period cannot be closed until it is resolved or waived

#### Scenario: Admin waives an exception with reason
- **WHEN** an admin waives a blocking exception with a reason
- **THEN** the system records the waiver actor, timestamp, reason, and previous exception state in the finance audit log

### Requirement: Period close validation
The system SHALL prevent closing a finance period while blocking exceptions remain unresolved or unwaived. Closing a period SHALL snapshot summary totals and record the close actor and timestamp.

#### Scenario: Period close blocked by unresolved exception
- **WHEN** an admin attempts to close a review period with unresolved blocking exceptions
- **THEN** the system rejects the close action and returns the blocking exception list

#### Scenario: Period closes after exceptions resolved
- **WHEN** all blocking exceptions are resolved or waived
- **THEN** the admin can close the period and the system records closed totals and a close audit event

### Requirement: Finance audit log
The system SHALL maintain an append-only finance audit log for period creation, status changes, exception waivers, settings changes, document reference changes, export generation, export acceptance, and reopen actions. Audit entries SHALL include actor, timestamp, action, target type, target id, request id when available, and a redacted before/after payload when applicable.

#### Scenario: Document reference edit is audited
- **WHEN** an admin changes an accounting document reference for an order
- **THEN** the system stores a finance audit event with the old value, new value, actor, timestamp, and reason if provided
