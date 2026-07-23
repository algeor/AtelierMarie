## ADDED Requirements

### Requirement: Product discount data model
A product SHALL support an optional percentage discount defined by three fields: `discount_percent` (integer 1–99, nullable), `discount_starts_at` (UTC timestamp text stored as `YYYY-MM-DD HH:MM:SS`, nullable), and `discount_ends_at` (same format, nullable). API writes SHALL normalize timezone-aware ISO-8601 datetimes to the stored UTC format and SHALL reject timezone-less datetime input except for the canonical stored UTC format. When `discount_percent` is NULL the product has no discount. The model SHALL reject a percent outside 1–99, and SHALL reject a window where `discount_starts_at >= discount_ends_at` when both are set. A date without a resulting `discount_percent` SHALL be rejected.

#### Scenario: Product with no discount
- **WHEN** a product has `discount_percent` = NULL
- **THEN** the product is considered to have no discount and its effective price equals `price_cents`

#### Scenario: Reject out-of-range percent
- **WHEN** an admin submits `discount_percent` = 0 or 100
- **THEN** the request is rejected with a validation error

#### Scenario: Reject inverted window
- **WHEN** an admin submits `discount_starts_at` later than or equal to `discount_ends_at`
- **THEN** the request is rejected with a validation error

#### Scenario: Normalize timezone-aware datetime
- **WHEN** an admin submits `discount_starts_at` = `2026-08-01T12:30:00+03:00`
- **THEN** the stored value is normalized to UTC canonical text `2026-08-01 09:30:00`

#### Scenario: Reject timezone-less non-canonical datetime
- **WHEN** an admin submits `discount_starts_at` = `2026-08-01T12:30:00` without a timezone
- **THEN** the request is rejected with a validation error

#### Scenario: Clearing discount clears stale bounds
- **WHEN** an admin updates a product by setting `discount_percent` = NULL
- **THEN** `discount_percent`, `discount_starts_at`, and `discount_ends_at` are all stored as NULL

### Requirement: Discount active window
A discount SHALL be considered **active** at a given moment when `discount_percent` is not NULL AND (`discount_starts_at` is NULL OR now ≥ `discount_starts_at`) AND (`discount_ends_at` is NULL OR now ≤ `discount_ends_at`). `now` and stored bounds SHALL be compared as canonical UTC timestamp strings. Both window bounds are inclusive. A discount with a percent but no dates is active indefinitely (manual on/off).

#### Scenario: Manual discount with no dates is active
- **WHEN** a product has `discount_percent` = 20 and both dates NULL
- **THEN** the discount is active

#### Scenario: Scheduled discount before its window
- **WHEN** now is earlier than `discount_starts_at`
- **THEN** the discount is NOT active and the effective price equals `price_cents`

#### Scenario: Scheduled discount after its window
- **WHEN** now is later than `discount_ends_at`
- **THEN** the discount is NOT active

#### Scenario: Scheduled discount exactly at start boundary
- **WHEN** now equals `discount_starts_at`
- **THEN** the discount is active (inclusive start)

#### Scenario: Scheduled discount exactly at end boundary
- **WHEN** now equals `discount_ends_at`
- **THEN** the discount is active (inclusive end)

### Requirement: Effective price computation
The system SHALL compute a product's effective price via a single shared helper used by all price consumers (public API, cart totals, checkout snapshot). When a discount is active the effective price SHALL be `round_half_up(price_cents × (100 − discount_percent) / 100)` computed with integer arithmetic, and SHALL be clamped to a minimum of 1 cent. When no discount is active the effective price SHALL equal `price_cents`.

#### Scenario: Effective price with active discount
- **WHEN** `price_cents` = 3250 and an active `discount_percent` = 20
- **THEN** the effective price is 2600

#### Scenario: Round half up to nearest cent
- **WHEN** `price_cents` = 999 and an active `discount_percent` = 15
- **THEN** the effective price is 849 (849.15 rounded)

#### Scenario: Floor clamp prevents zero price
- **WHEN** `price_cents` = 1 and an active `discount_percent` = 99
- **THEN** the effective price is clamped to 1 cent (never 0), satisfying `order_items CHECK (price_cents > 0)`

#### Scenario: No discount returns list price
- **WHEN** a product has no active discount
- **THEN** the effective price equals `price_cents` unchanged
