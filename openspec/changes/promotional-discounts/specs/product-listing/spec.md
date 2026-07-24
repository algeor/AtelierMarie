## ADDED Requirements

### Requirement: Product card shows active discount
When a product has an active discount, its card SHALL display the `effective_price_cents` as the primary price, the original `price_cents` struck through, and a `−X%` discount badge. When no discount is active the card SHALL display `price_cents` as before with no badge.

#### Scenario: Card with active discount
- **WHEN** a product card renders for a product with `price_cents` = 3250, `effective_price_cents` = 2600, `discount_active` = true, `discount_percent` = 20
- **THEN** the card shows "€26.00" as the price, "€32.50" struck through, and a "−20%" badge

#### Scenario: Card without discount unchanged
- **WHEN** a product card renders for a product with `discount_active` = false
- **THEN** the card shows only the regular price (`price_cents`) with no strikethrough or badge
