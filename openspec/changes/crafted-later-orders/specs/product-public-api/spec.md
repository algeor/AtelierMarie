## ADDED Requirements

### Requirement: Public product responses expose orderability and availability state
Public product list and detail responses SHALL expose `can_order`, `available_now`, `availability_status`, and `ships_when_complete`. For active products, `can_order` SHALL be `true` even when `stock = 0`. `availability_status` SHALL be `in_stock` when `stock > 0` and `crafted_later` when `stock = 0`.

#### Scenario: In-stock product shows immediate availability
- **WHEN** a public product response is built for an active product with `stock > 0`
- **THEN** the response includes `can_order = true`, `available_now = true`, `availability_status = in_stock`, and `ships_when_complete = true`

#### Scenario: Out-of-stock product remains orderable
- **WHEN** a public product response is built for an active product with `stock = 0`
- **THEN** the response includes `can_order = true`, `available_now = false`, `availability_status = crafted_later`, and `ships_when_complete = true`
