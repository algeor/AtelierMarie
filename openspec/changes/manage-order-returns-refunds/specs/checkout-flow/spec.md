## ADDED Requirements

### Requirement: Abandoned card payments require admin review before fulfillment
The system SHALL place abandoned or expired card-payment orders into an admin payment review state. Such orders MUST NOT be shipped or handed to a courier unless an admin records customer confirmation and resolves the payment method.

#### Scenario: Card checkout expires
- **WHEN** a card order's Stripe checkout session expires without payment
- **THEN** the order remains unfulfilled, payment status becomes `review_required`, and the order appears in the abandoned-payment admin review queue

#### Scenario: Abandoned card order cannot be shipped
- **WHEN** an admin attempts to ship an abandoned card order that is still in payment review
- **THEN** the system rejects the transition and does not create or require a courier shipment

### Requirement: Admin-confirmed abandoned card orders can convert to payment on delivery
The system SHALL allow an abandoned card order to be converted to payment on delivery only after an admin records that the customer confirmed the order. The system SHALL preserve the original attempted payment method for audit.

#### Scenario: Customer confirms abandoned card order by phone
- **WHEN** an admin records callback confirmation for an abandoned card order and chooses payment on delivery
- **THEN** the order becomes eligible for normal admin confirmation/shipping with payment method COD and payment status `cod_pending`

#### Scenario: Original card attempt remains auditable
- **WHEN** an abandoned card order is converted to payment on delivery
- **THEN** the system retains the original card checkout/payment attempt data in payment records or audit events

### Requirement: Unconfirmed abandoned card orders release stock when closed
The system SHALL release stock for abandoned card orders when the admin cancels them or when the configured reservation expiry closes them without customer confirmation.

#### Scenario: Admin cancels unconfirmed abandoned card order
- **WHEN** an admin cancels an abandoned card order after the customer does not confirm
- **THEN** the order is cancelled, stock is restored, and no refund is created

#### Scenario: Reservation expiry releases unconfirmed abandoned card order
- **WHEN** an abandoned card order remains unconfirmed past the configured reservation expiry
- **THEN** the system releases the reserved stock and keeps an audit record of the expiration
