## Purpose

Defines the storefront order confirmation experience, including order summaries, status messaging, and post-checkout guidance.
## Requirements
### Requirement: Order confirmation page displays order details
The system SHALL provide a `/orders/[id]/confirmation` page that displays the order ID, all ordered items (name, quantity, unit price), the order total, and a "Thank you for your order!" message. The page SHALL fetch order data from `GET /v1/orders/{id}`.

#### Scenario: Successful order confirmation display
- **WHEN** user is redirected to `/orders/abc-123/confirmation` after checkout
- **THEN** the page shows order ID "abc-123", each item with name/quantity/price, the total, and a thank-you heading

#### Scenario: Order items show snapshot data
- **WHEN** the confirmation page renders
- **THEN** product names and prices are from the order snapshot (order_items), not fetched from current product catalog

### Requirement: Confirmation page handles invalid order
The system SHALL show a friendly error if the order ID does not exist or the session does not have access to it.

#### Scenario: Order not found
- **WHEN** user navigates to `/orders/nonexistent-id/confirmation`
- **THEN** a message "Order not found" is displayed with a link back to the shop

#### Scenario: Access denied
- **WHEN** user navigates to a confirmation page for an order that belongs to a different session
- **THEN** a message "Order not found" is displayed (same as not found — no information leakage)

### Requirement: Confirmation page provides next actions
The system SHALL display navigation options after the order details: a "Continue Shopping" link back to `/products` and a brief note acknowledging the customer's email on file.

#### Scenario: Continue shopping link
- **WHEN** the confirmation page renders
- **THEN** a "Continue Shopping" button/link navigates to `/products`

#### Scenario: Order contact note
- **WHEN** the confirmation page renders
- **THEN** a note states "Order confirmation noted for {email}" using the order's customer_email (no promise of email delivery)

### Requirement: Confirmation page refreshes cart state
The system SHALL re-fetch the cart via `GET /v1/cart` when the confirmation page mounts, syncing local state with the backend (which already cleared the cart during checkout). This approach avoids destructively clearing a legitimate cart if the user revisits the confirmation URL later with a new cart.

#### Scenario: Cart synced after checkout
- **WHEN** user lands on the confirmation page immediately after checkout
- **THEN** the CartContext re-fetches from the API, receives an empty cart, and the header badge is hidden

#### Scenario: Revisit with new cart intact
- **WHEN** user revisits a bookmarked confirmation URL while having items in a new cart
- **THEN** the cart re-fetch returns the current (non-empty) cart and does NOT clear it

### Requirement: Confirmation page is shareable
The system SHALL allow the confirmation page URL to be revisited (bookmarked or shared). Revisiting fetches the order again from the API.

#### Scenario: Revisit confirmation page
- **WHEN** user revisits `/orders/abc-123/confirmation` after initial redirect
- **THEN** the page fetches the order and displays it (or shows "Order not found" if session doesn't match)

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

