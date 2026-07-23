## ADDED Requirements

### Requirement: Product form supports discount fields
The admin product create/edit form SHALL provide inputs for `discount_percent` (integer 1–99, optional), `discount_starts_at`, and `discount_ends_at` (optional datetime pickers). The form SHALL validate client-side that percent is within 1–99, that a start is before an end when both are set, and that a percent is present when any date is set. When a discount is entered the form SHALL preview the resulting sale price. Leaving `discount_percent` empty SHALL submit no discount (clearing any existing one).

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
- **THEN** the discount is removed
