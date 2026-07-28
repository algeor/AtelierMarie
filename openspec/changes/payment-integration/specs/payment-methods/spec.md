## ADDED Requirements

### Requirement: Orders carry payment_method and payment_status fields
The system SHALL store `payment_method` and `payment_status` on every order row as independent axes from `order_status`. `payment_method` SHALL be one of `'cod'`, `'card'`, `'bank_transfer'` (default `'cod'`). `payment_status` SHALL be one of `'pending'`, `'paid'`, `'cod_pending'`, `'failed'`, `'refunded'` (default `'cod_pending'`). These fields SHALL be included in all order API responses (customer and admin).

#### Scenario: New COD order has correct payment fields
- **WHEN** a customer places an order with `payment_method='cod'`
- **THEN** the order is created with `payment_method='cod'` and `payment_status='cod_pending'`

#### Scenario: New card order has correct payment fields
- **WHEN** a customer places an order with `payment_method='card'`
- **THEN** the order is created with `payment_method='card'` and `payment_status='pending'`

#### Scenario: New bank transfer order has correct payment fields
- **WHEN** a customer places an order with `payment_method='bank_transfer'`
- **THEN** the order is created with `payment_method='bank_transfer'` and `payment_status='pending'`

#### Scenario: Default payment method is COD
- **WHEN** a customer places an order without specifying `payment_method`
- **THEN** the order is created with `payment_method='cod'` and `payment_status='cod_pending'`

#### Scenario: Existing orders without payment columns default to COD
- **WHEN** an order created before this change is retrieved
- **THEN** `payment_method` is `'cod'` and `payment_status` is `'cod_pending'`

#### Scenario: Invalid payment method rejected
- **WHEN** a customer sends `POST /v1/orders` with `payment_method='crypto'`
- **THEN** the API returns HTTP 422 with a validation error for the payment_method field

### Requirement: COD payment_status auto-advances to paid on delivery
The system SHALL automatically set `payment_status='paid'` for COD orders when `order_status` transitions to `'delivered'`. This SHALL happen in the same database transaction as the status update. No manual admin action is required.

#### Scenario: COD order payment marked paid on delivery
- **WHEN** an admin marks a COD order as `'delivered'`
- **THEN** `payment_status` is set to `'paid'` in the same transaction, without any additional admin action

#### Scenario: Non-COD order delivery does not auto-advance payment_status
- **WHEN** an admin marks a card order as `'delivered'`
- **THEN** `payment_status` is unchanged by the delivery transition (it was already `'paid'` from the webhook)

#### Scenario: COD cancellation does not mark payment paid
- **WHEN** an admin cancels a COD order before delivery
- **THEN** `payment_status` remains `'cod_pending'` (no money was collected)
