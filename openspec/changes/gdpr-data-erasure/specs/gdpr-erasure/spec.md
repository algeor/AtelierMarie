## ADDED Requirements

### Requirement: Consolidated data-subject erasure

The system SHALL provide a service operation that erases a data subject's personal data across all
Layer 1 tables (`orders`, `order_emails`, `comments`, `contact_messages`, `users`, `sessions`),
given any subset of the identifiers email, `user_id`, and `session_id`. The operation SHALL run
within a single database transaction and SHALL be idempotent. It SHALL NOT delete
`suppressed_emails` entries (see the retention sweep for their bounded age-out).

#### Scenario: Erase order PII on all matched orders regardless of age

- **WHEN** erasure runs for a subject with orders matched by `customer_email`, `user_id`, or
  `session_id`
- **THEN** `customer_email`, `customer_name`, `delivery_details`, and `notes` on **all** their
  orders are overwritten with an `[erased]` placeholder or NULL, independent of the order's age
- **AND** `total_cents`, the order `status`, and all `order_items` snapshot rows are left unchanged

#### Scenario: Erase email audit trail

- **WHEN** erasure runs for a subject with `order_emails` rows
- **THEN** the `recipient` on those rows is overwritten with the `[erased]` placeholder
- **AND** the `status`, `event`, and timestamp columns are left unchanged so the send audit shape is
  preserved and the `idx_order_emails_sent_unique` index is not disturbed

#### Scenario: Hard-delete comments

- **WHEN** erasure runs for a subject with `comments` matched by `user_id` or `session_id`
- **THEN** those comment rows are deleted outright (not anonymized)

#### Scenario: Erase logged-in user record

- **WHEN** erasure runs for a subject identified by `user_id` or email that matches a `users` row
- **THEN** the row's `email` and `google_id` (both `UNIQUE NOT NULL`) are overwritten with
  per-subject unique placeholders derived from the row id (e.g. `erased-<id>@invalid`, `erased-<id>`)
- **AND** `name` and `avatar_url` are set to NULL
- **AND** the subject's active `sessions` rows are deleted

#### Scenario: Erase contact-form submissions

- **WHEN** erasure runs for a subject whose email matches `contact_messages` rows
- **THEN** the PII on those rows (`name`, `email`, `message`, `ip_address`) is removed or NULL-ified

#### Scenario: Suppression record is retained

- **WHEN** erasure runs for a subject who is on the `suppressed_emails` do-not-contact list
- **THEN** their suppression entry is left in place so the shop cannot inadvertently re-contact them

#### Scenario: Idempotent re-run

- **WHEN** erasure is run a second time for the same already-erased subject
- **THEN** no rows are changed and the operation completes successfully

#### Scenario: Subject resolution across anonymous and logged-in records

- **WHEN** a subject has an anonymous order keyed by `session_id` and a later order keyed by
  `user_id`, and both are passed to erasure
- **THEN** PII on both orders is erased in the same run
