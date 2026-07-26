## MODIFIED Requirements

### Requirement: Checkout converts cart to payment-aware order atomically
The system SHALL accept a selected payment method during checkout. For card
payment, checkout SHALL create a local order/payment record with a 15-minute
reservation, decrement stock, clear the cart, create a Stripe Checkout Session, and
return the Stripe redirect URL. For pay on delivery, checkout SHALL create a real
order with `payment_status = pending_collection`, decrement stock, clear the cart,
and return the order without Stripe redirect.

#### Scenario: Successful card checkout creates pending payment
- **WHEN** a session with valid cart and delivery details selects card payment
- **THEN** the backend creates an order with fulfillment status `pending`, payment
  method `stripe`, payment status `pending`, a `reserved_until` about 15 minutes in
  the future, and a Stripe Checkout URL
- **AND** stock is decremented and the cart is cleared atomically with order
  creation

#### Scenario: Successful pay-on-delivery checkout creates collection-pending order
- **WHEN** a session with valid cart and delivery details selects pay on delivery
- **THEN** the backend creates an order with fulfillment status `pending`, payment
  method `pay_on_delivery`, payment status `pending_collection`, stock decremented,
  and cart cleared
- **AND** no Stripe session is created

#### Scenario: Pay on delivery above cap rejected
- **WHEN** a customer selects pay on delivery for an order total above 5000 cents
- **THEN** the backend rejects checkout and does not create an order

#### Scenario: Disabled payment method rejected
- **WHEN** checkout requests a payment method disabled in site settings
- **THEN** the backend rejects checkout and does not create an order or payment

#### Scenario: Both payment methods cannot be unavailable
- **WHEN** public checkout loads payment settings
- **THEN** at least one payment method is available, or checkout shows an
  unavailable-payment error rather than allowing submission

### Requirement: Order response includes payment summary
The system SHALL include public order number, payment method, payment status,
reservation expiry when relevant, paid/collected timestamps when relevant, and
payment labels needed by customer and admin UI.

#### Scenario: Card order response includes reservation
- **WHEN** a pending card order is retrieved
- **THEN** the response includes `order_number`, `payment_method = stripe`,
  `payment_status = pending`, and `reserved_until`

#### Scenario: Pay-on-delivery order response includes collection status
- **WHEN** a pay-on-delivery order is retrieved
- **THEN** the response includes `payment_method = pay_on_delivery` and
  `payment_status = pending_collection`

### Requirement: Order emails respect payment method
The system SHALL queue customer order email after Stripe payment is confirmed paid.
Pay-on-delivery orders SHALL queue customer order email immediately after order
creation. Expired/cancelled unpaid card attempts SHALL NOT send customer email in
MVP.

#### Scenario: Card order email delayed until paid
- **WHEN** a card checkout creates a pending payment order
- **THEN** no customer order email is queued until a verified Stripe success event
  marks payment paid

#### Scenario: Pay-on-delivery email immediate
- **WHEN** a pay-on-delivery order is created
- **THEN** the normal customer order email is queued in the order transaction
