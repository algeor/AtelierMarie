## ADDED Requirements

### Requirement: Product detail shows active discount
The product detail page SHALL display the `effective_price_cents` as the primary price, the original `price_cents` struck through, and a `−X%` discount badge when a discount is active. Add-to-cart SHALL operate on the discounted product; the effective price is authoritative at checkout regardless of what was displayed. When no discount is active the page SHALL display `price_cents` with no strikethrough or badge.

#### Scenario: Detail page with active discount
- **WHEN** the detail page renders for a product with `price_cents` = 3250, `effective_price_cents` = 2600, `discount_active` = true, `discount_percent` = 20
- **THEN** the page shows "€26.00" as the price, "€32.50" struck through, and a "−20%" badge

#### Scenario: Detail page without discount unchanged
- **WHEN** the detail page renders for a product with `discount_active` = false
- **THEN** the page shows only the regular price with no strikethrough or badge
