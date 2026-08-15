## MODIFIED Requirements

### Requirement: Add-to-cart button on product cards and detail page
The system SHALL display an `Add to Cart` button on active products even when `stock = 0`. Clicking the button SHALL call `addToCart`, show a brief confirmation state, and update the header badge. For products that are not available now, the UI SHALL communicate that the item will be crafted later rather than replacing the button with a disabled out-of-stock state.

#### Scenario: Add to cart from product card while in stock
- **WHEN** user clicks `Add to Cart` on an active in-stock product card
- **THEN** the cart is updated and the drawer opens

#### Scenario: Add to cart from product card while crafted later
- **WHEN** user clicks `Add to Cart` on an active product with `stock = 0`
- **THEN** the cart is updated successfully
- **AND** the UI communicates that the item will be crafted later

#### Scenario: Button disabled only for inactive or in-flight states
- **WHEN** a product is active and no request is in flight
- **THEN** the add-to-cart control remains interactive regardless of current stock

### Requirement: Cart drawer quantity controls respect cart limits, not stock caps
The cart drawer SHALL allow quantity changes up to the configured per-item cart limit instead of capping increments at the product's current stock.

#### Scenario: Drawer allows increment beyond current stock
- **WHEN** an active product in the cart has `stock = 0` or current quantity equals stock
- **THEN** the increment control remains available until the configured cart limit is reached

#### Scenario: Drawer still enforces per-item cap
- **WHEN** the cart quantity reaches the configured per-item maximum
- **THEN** further increments are blocked and the quantity-limit message is shown
