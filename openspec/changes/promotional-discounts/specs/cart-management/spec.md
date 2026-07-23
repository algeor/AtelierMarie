## MODIFIED Requirements

### Requirement: View cart contents
The system SHALL provide `GET /v1/cart` that returns all cart items for the current session with embedded product details and computed totals. Inactive/deactivated products SHALL be excluded from the main `items` list but reported in an `unavailable_items` list with human-readable details. Line and total pricing SHALL use each product's **effective price** (the discounted price when a discount is active), so the cart reflects promotional pricing. Embedded product details SHALL include `price_cents`, `effective_price_cents`, `discount_percent`, and `discount_active`.

#### Scenario: View cart with items
- **WHEN** the session has 2 items in the cart (both products active)
- **THEN** the response is 200 with `items` (array of 2 CartItemResponse with embedded product details), `total_cents` (sum of effective_price × quantity), and `item_count` (sum of quantities)

#### Scenario: View empty cart
- **WHEN** the session has no items in the cart
- **THEN** the response is 200 with `items: []`, `total_cents: 0`, `item_count: 0`, `unavailable_items: []`

#### Scenario: Cart item references deactivated product
- **WHEN** a cart item references a product with `is_active = 0`
- **THEN** that item is excluded from `items` and reported in `unavailable_items` as `{"product_id": "...", "product_name": "...", "reason": "deactivated"}`

#### Scenario: Cart total reflects an active discount
- **WHEN** the cart contains 2 units of a product with `price_cents` = 3250 and an active 20% discount
- **THEN** the line uses `effective_price_cents` = 2600 and contributes 5200 to `total_cents`

**Design note:** Including `product_name` in `unavailable_items` is an intentional UX choice — users need to know which of their saved items became unavailable. The information was already visible when the product was active. For a family candle business, deactivation reasons are benign (seasonal rotation, sold out permanently). If catalog secrecy ever becomes a concern, `product_name` can be replaced with a generic label without breaking the contract shape.
