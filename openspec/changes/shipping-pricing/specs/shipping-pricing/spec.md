## ADDED Requirements

### Requirement: Real-time shipping cost calculation
The system SHALL calculate shipping cost per courier via the Speedy and Econt calculation APIs, based on destination and total cart weight, exposed through `POST /v1/delivery/calculate`.

Cart weight SHALL be the sum of each line item's `products.weight_grams` (default 300g) times quantity, plus `PACKAGING_WEIGHT_GRAMS` (200g).

#### Scenario: Approximate price after city selection
- **WHEN** a caller requests calculation with a courier, method, and city (no specific office/address)
- **THEN** the system returns an approximate `shipping_cents` for that courier suitable for side-by-side comparison

#### Scenario: Exact price after specific destination
- **WHEN** a caller requests calculation with a courier, method, and a specific `office_id` (office) or full address (door)
- **THEN** the system returns the exact `shipping_cents` for that destination

#### Scenario: Both couriers returned for comparison
- **WHEN** a caller requests calculation for both Speedy and Econt in one call
- **THEN** the system returns a price entry per courier so the UI can compare them

### Requirement: Free shipping threshold
The system SHALL set `shipping_cents = 0` when `items_total_cents >= 5000` (€50), server-enforced regardless of the client-submitted value.

#### Scenario: Order qualifies for free shipping
- **WHEN** the cart items subtotal is €50 or more
- **THEN** the calculated and enforced `shipping_cents` is 0 for any courier

#### Scenario: Order below threshold pays shipping
- **WHEN** the cart items subtotal is below €50
- **THEN** the system returns the courier-calculated `shipping_cents`

### Requirement: Fallback pricing on courier API failure
The system SHALL return a flat `FALLBACK_SHIPPING_CENTS` (500) when a courier's calculation API times out or errors, so checkout is never blocked by an external outage. Fallback is evaluated per-courier and only after the free-shipping short-circuit, so a qualifying order is never charged a fallback price.

#### Scenario: Courier API times out
- **WHEN** a courier calculation API does not respond within the timeout budget
- **THEN** the system returns `FALLBACK_SHIPPING_CENTS` for that courier and logs the failure without raising to the caller

#### Scenario: One courier down, the other up
- **WHEN** one courier's API fails but the other responds
- **THEN** the responding courier's quote carries its live price and the failed courier's quote carries the fallback price, each independently

### Requirement: Price provenance
Each shipping quote SHALL record how its price was derived via a `price_source` of `live`, `table`, or `flat`, and an `is_fallback` flag that is true whenever `price_source` is not `live`. In this phase only `live` and `flat` are produced; `table` is reserved for a follow-on shaped-fallback phase.

#### Scenario: Live price carries live provenance
- **WHEN** a courier calculation API returns a price within the timeout budget
- **THEN** the quote has `price_source = "live"` and `is_fallback = false`

#### Scenario: Fallback price carries fallback provenance
- **WHEN** a quote is produced by the flat fallback
- **THEN** the quote has `price_source = "flat"` and `is_fallback = true`
