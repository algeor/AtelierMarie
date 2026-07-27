## ADDED Requirements

### Requirement: Shipping cost included and validated at checkout
`POST /v1/orders` SHALL persist `shipping_cents` on the order such that `total_cents = items_total_cents + shipping_cents`. The server SHALL re-derive and enforce `shipping_cents` (free-shipping threshold and a bounded range check) rather than trusting the client-submitted value.

#### Scenario: Total reflects shipping
- **WHEN** an order is placed with a non-zero shipping cost
- **THEN** the persisted `total_cents` equals `items_total_cents + shipping_cents`

#### Scenario: Free-shipping enforced server-side
- **WHEN** the client submits a non-zero `shipping_cents` but the items subtotal is >= €50
- **THEN** the server overrides `shipping_cents` to 0

#### Scenario: Out-of-range shipping rejected
- **WHEN** the client submits a `shipping_cents` outside the accepted bounded range
- **THEN** the server rejects the request with a validation error (422)

### Requirement: Shipping price provenance persisted on the order
`POST /v1/orders` SHALL persist the price provenance of the selected shipping quote on the order: `price_source` (`live`/`table`/`flat`), `is_fallback`, and `quoted_at`. This makes every order's shipping price auditable and enables later reconciliation against the courier invoice.

#### Scenario: Live-priced order records live provenance
- **WHEN** an order is placed with a shipping price that was quoted live
- **THEN** the persisted order records `price_source = "live"` and `is_fallback = false`

#### Scenario: Fallback-priced order records fallback provenance
- **WHEN** an order is placed while the courier API was unavailable and a fallback price was used
- **THEN** the persisted order records `is_fallback = true` and the corresponding `price_source`
