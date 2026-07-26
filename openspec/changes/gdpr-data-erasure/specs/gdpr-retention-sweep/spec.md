## ADDED Requirements

### Requirement: Scheduled retention sweep

The system SHALL run a background sweep, on the existing hourly cleanup loop, that enforces
storage-limitation (GDPR Art. 5(1)(e)) by hard-deleting records past their retention window. The
sweep SHALL catch and log its own errors and MUST NOT propagate failures into request handling.

#### Scenario: Hard-delete orders past the retention window

- **WHEN** the sweep runs and finds orders whose `created_at` is older than `data_retention_years`
- **THEN** those orders are hard-deleted along with **all three** FK children —
  `order_emails`, `order_email_send_claims`, and `order_items` — children deleted first and the
  order row last, within a transaction (foreign-key enforcement is ON)

#### Scenario: Age out suppressed emails

- **WHEN** the sweep runs and finds `suppressed_emails` rows older than the configured age-out period
- **THEN** those rows are deleted

#### Scenario: Age out contact messages

- **WHEN** the sweep runs and finds `contact_messages` older than `contact_message_retention_days`
- **THEN** those rows are deleted (existing behavior is preserved and run alongside the new sweep)

#### Scenario: Retained orders within the window are untouched

- **WHEN** the sweep runs and an order's `created_at` is within `data_retention_years`
- **THEN** that order and its children are left in place

#### Scenario: Sweep failure does not break the app

- **WHEN** the retention sweep raises an unexpected error
- **THEN** the error is logged and the cleanup loop continues; request handling is unaffected
