## ADDED Requirements

### Requirement: Checkout legal and privacy disclosure
The checkout page SHALL display a small legal/privacy disclosure near every visible Place Order button. The disclosure SHALL link to localized Terms & Conditions and Privacy Policy pages and SHALL state that order submission involves processing the provided contact and delivery data.

#### Scenario: Desktop checkout disclosure includes policy links
- **WHEN** checkout renders on desktop
- **THEN** the disclosure near the desktop Place Order button links to Terms & Conditions and Privacy Policy

#### Scenario: Mobile checkout disclosure includes policy links
- **WHEN** checkout renders on mobile
- **THEN** the disclosure near the mobile Place Order button links to Terms & Conditions and Privacy Policy

### Requirement: Checkout order summary uses charged item prices
The checkout order summary SHALL use each cart item's effective charged price for line totals and subtotal display. If a product has an active discount, the summary SHALL NOT calculate line totals from the original list price.

#### Scenario: Discounted cart item summary uses effective price
- **WHEN** a cart item has `price_cents = 4000`, `effective_price_cents = 3000`, and quantity 2
- **THEN** checkout displays the line total as 6000 cents equivalent
- **AND** the subtotal matches the cart total returned by the cart API

### Requirement: Checkout shipping and total clarity
Checkout SHALL show shipping cost information only when it is known and included in the order total. If shipping pricing is not implemented or shipping is zero, the UI SHALL avoid implying that a paid courier delivery charge is included.

#### Scenario: Known shipping is shown before submission
- **WHEN** checkout has a known `shipping_cents` value
- **THEN** the order summary displays item subtotal, shipping, and final total before order submission

#### Scenario: Unknown shipping is not misrepresented
- **WHEN** checkout does not have a real shipping price
- **THEN** the UI does not present a paid shipping amount as included in the order total
