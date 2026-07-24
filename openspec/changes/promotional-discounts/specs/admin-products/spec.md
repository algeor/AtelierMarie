## ADDED Requirements

### Requirement: Product form supports discount fields
The admin product create/edit form SHALL provide inputs for `discount_percent` (integer 1–99, optional), `discount_starts_at`, and `discount_ends_at` (optional datetime pickers). The form SHALL validate client-side that percent is within 1–99, that a start is before an end when both are set, and that a percent is present when any date is set. The form SHALL convert browser-local datetime input to timezone-aware UTC values before submitting, and SHALL convert stored UTC values back to local datetime input values when editing. When a discount is entered the form SHALL preview the resulting sale price. Leaving `discount_percent` empty SHALL submit `discount_percent = null` and clear both datetime fields.

#### Scenario: Set a manual discount
- **WHEN** admin enters `discount_percent` = 20 with no dates and submits
- **THEN** the product is saved with a manual (always-on) discount

#### Scenario: Set a scheduled discount
- **WHEN** admin enters `discount_percent` = 30 with a start and end date and submits
- **THEN** the product is saved with the scheduled window

#### Scenario: Client-side validation blocks invalid window
- **WHEN** admin sets an end date earlier than the start date
- **THEN** an inline validation error is shown and the form is not submitted

#### Scenario: Clearing the discount
- **WHEN** admin blanks the `discount_percent` field on a discounted product and submits
- **THEN** the submitted payload clears `discount_percent`, `discount_starts_at`, and `discount_ends_at`

#### Scenario: Edit scheduled discount displays local time
- **WHEN** admin edits a product whose stored `discount_starts_at` is `2026-08-01 09:30:00` UTC
- **THEN** the datetime picker displays the equivalent local browser time
