## MODIFIED Requirements

### Requirement: Order state machine remains fulfillment-focused
The order fulfillment status SHALL remain separate from payment status. A paid card
order SHALL remain fulfillment `pending` until the owner/admin confirms it.

#### Scenario: Paid card order still awaits owner confirmation
- **WHEN** Stripe webhook marks a card payment paid
- **THEN** `payment_status` becomes `paid`
- **AND** `orders.status` remains `pending`

### Requirement: Cancellation restores stock for unpaid and COD orders
Cancelling an order SHALL restore stock according to the existing cancellation
rules. For expired unpaid card reservations, cancellation SHALL happen through the
payment expiry cleanup. For admin-cancelled pay-on-delivery orders, cancellation
SHALL restore stock and record a payment event.

#### Scenario: Expired card payment cancellation restores stock
- **WHEN** expiry cleanup cancels an unpaid card order
- **THEN** product stock is restored for every order item

#### Scenario: Admin cancels pay-on-delivery order
- **WHEN** admin cancels a pay-on-delivery order before collection
- **THEN** fulfillment status becomes `cancelled`, payment status becomes
  `cancelled`, stock is restored, and a payment event is recorded

### Requirement: Revenue counts only paid or collected orders
Revenue metrics SHALL include only orders with payment status `paid` or
`collected`. Pending, failed, cancelled, unpaid, and review-required payments SHALL
be excluded from revenue totals.

#### Scenario: Dashboard excludes pending card payment
- **WHEN** dashboard revenue is calculated
- **THEN** pending card orders are not included in revenue

#### Scenario: Dashboard includes collected COD order
- **WHEN** a pay-on-delivery order is marked collected
- **THEN** dashboard revenue includes that order total
