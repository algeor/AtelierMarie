## MODIFIED Requirements

### Requirement: Decision tree for product states
When `page.tsx` receives a product response it SHALL apply this logic in order: (1) if product not found or fetch throws → `notFound()`; (2) if `is_active === false` → `notFound()`; (3) if `can_order === true` and `available_now === false` → render the full page with ordering controls and crafted-later messaging; (4) if `can_order === true` and `available_now === true` → render the full page with ordering controls; (5) otherwise render a non-purchasable state.

#### Scenario: Active product with zero stock remains purchasable
- **WHEN** the product is active, `stock = 0`, and `can_order = true`
- **THEN** the page renders ordering controls
- **AND** shows crafted-later messaging instead of a disabled out-of-stock button

#### Scenario: Inactive product still treated as not found
- **WHEN** the product is inactive
- **THEN** the page calls `notFound()` and does not render purchase UI

### Requirement: Quantity selector
The system SHALL provide a quantity selector allowing users to choose how many units to add to cart. The maximum selectable quantity SHALL respect the configured storefront cart limit rather than current stock.

#### Scenario: Maximum quantity respects cart cap
- **WHEN** the quantity reaches the configured per-item limit
- **THEN** the quantity cannot increase further and the `+` control appears disabled

#### Scenario: Quantity selector rendered for crafted-later products
- **WHEN** a product is orderable but not currently available now
- **THEN** the QuantitySelector component is still rendered

### Requirement: Add to Cart button
The product detail page SHALL display an `Add to Cart` button for orderable products. For crafted-later products the control SHALL remain interactive and SHALL communicate that the order will ship when complete.

#### Scenario: Crafted-later detail purchase
- **WHEN** a user clicks `Add to Cart` on a product with `availability_status = crafted_later`
- **THEN** the action succeeds
- **AND** the page shows feedback that the item will be crafted after purchase and ships when the full order is ready
