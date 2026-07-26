## MODIFIED Requirements

### Requirement: Checkout page supports payment method selection
The checkout page SHALL fetch safe public payment settings and render enabled
payment methods. When both card and pay on delivery are enabled, card payment SHALL
be selected by default. Disabled payment methods SHALL NOT be selectable.

#### Scenario: Both methods enabled
- **WHEN** card and pay on delivery are enabled
- **THEN** checkout shows both `Card payment` and `Pay on delivery`, with card
  selected by default

#### Scenario: Card copy shown
- **WHEN** card payment is selected
- **THEN** checkout shows `Your items are reserved for 15 minutes while you complete card payment.`

#### Scenario: Pay-on-delivery copy shown
- **WHEN** pay on delivery is selected
- **THEN** checkout shows `Payment is collected when your order is delivered. Available up to EUR 50.`

### Requirement: Card checkout redirects to Stripe
The checkout page SHALL submit valid checkout details to the backend and redirect
to the returned Stripe Checkout URL for card payments. It SHALL preserve user input
on validation/network errors.

#### Scenario: Card submit redirects
- **WHEN** customer submits valid checkout with card payment selected
- **THEN** the frontend receives a Stripe URL and redirects the browser to Stripe

#### Scenario: Disabled method error shown
- **WHEN** backend rejects checkout because the selected payment method was disabled
- **THEN** checkout shows an actionable error and does not clear form fields

### Requirement: Stripe return page fetches payment status
After Stripe success or cancel return, the frontend SHALL fetch backend
order/payment status using the order id and return token. It SHALL NOT show payment
success solely because Stripe redirected to the success URL.

#### Scenario: Paid status shown after webhook
- **WHEN** Stripe return page loads and backend reports `payment_status = paid`
- **THEN** the page shows `Payment received`

#### Scenario: Pending status shown before webhook
- **WHEN** Stripe return page loads before the webhook has marked payment paid
- **THEN** the page shows `Payment processing`

#### Scenario: Pay-on-delivery confirmation copy
- **WHEN** a pay-on-delivery order confirmation page loads
- **THEN** the page shows `Order received. Payment will be collected on delivery.`

### Requirement: Customer order history shows payment attempts clearly
Customer order history SHALL include pending and cancelled card payment attempts,
but they SHALL be clearly marked as payment pending/cancelled and not presented as
active fulfilled orders or revenue.

#### Scenario: Pending card attempt visible
- **WHEN** a customer has a pending card payment attempt within the reservation
  window
- **THEN** order history shows it with `Payment pending`

#### Scenario: Cancelled card attempt visible
- **WHEN** a card payment attempt expired or was cancelled
- **THEN** order history shows it with `Payment cancelled`
