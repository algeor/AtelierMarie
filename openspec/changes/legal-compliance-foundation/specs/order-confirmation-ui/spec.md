## ADDED Requirements

### Requirement: Order confirmation includes legal policy references
The order confirmation page SHALL show localized links to Terms & Conditions and Privacy Policy, and SHALL make withdrawal/returns information discoverable from the confirmation state.

#### Scenario: Confirmation links policies
- **WHEN** an order confirmation page renders successfully
- **THEN** it includes links to Terms & Conditions and Privacy Policy
- **AND** the Terms link makes withdrawal and returns information discoverable

### Requirement: Order confirmation shows price breakdown
The order confirmation page SHALL display item subtotal, shipping, and final total using fields from the order response. If shipping is zero, the page SHALL show that clearly or omit the row only when the total cannot be misunderstood.

#### Scenario: Confirmation shows shipping breakdown
- **WHEN** an order response includes `items_total_cents`, `shipping_cents`, and `total_cents`
- **THEN** the confirmation page displays a consistent subtotal, shipping, and total breakdown
