## ADDED Requirements

### Requirement: Bank transfer orders display IBAN instructions in UI and email
The system SHALL display IBAN, BIC, bank name, and payment reference to the customer when `payment_method='bank_transfer'`, both on the order confirmation page and in the `payment_pending` email. IBAN, BIC, and bank name SHALL come from settings config (`BANK_IBAN`, `BANK_BIC`, `BANK_NAME`). The payment reference SHALL be the short order ID (`order_id_short`). Bank transfer SHALL only be offered at checkout when `BANK_IBAN` is configured.

#### Scenario: Bank transfer order confirmation shows IBAN
- **WHEN** a customer places a bank_transfer order and views the order confirmation page
- **THEN** the page displays IBAN, BIC, bank name, and payment reference equal to the short order ID

#### Scenario: Bank transfer payment_pending email includes IBAN
- **WHEN** a bank_transfer order is created
- **THEN** the `payment_pending` email sent to the customer includes IBAN, BIC, bank name, and the order reference

#### Scenario: Bank transfer not offered when BANK_IBAN not configured
- **WHEN** `BANK_IBAN` is empty in settings
- **THEN** `bank_transfer` is not a valid `payment_method` at checkout (422 if submitted)

### Requirement: Admin can manually mark bank transfer payment received
The system SHALL expose `PATCH /v1/admin/orders/{id}/payment` (admin-only) that sets `payment_status='paid'` for a bank_transfer order currently in `payment_status='pending'`. On success the `placed` email SHALL be queued for the customer. Calling this endpoint on an already-paid order SHALL return HTTP 409.

#### Scenario: Admin marks bank transfer payment received
- **WHEN** an admin sends `PATCH /v1/admin/orders/{id}/payment` with `{"payment_status": "paid"}` for a bank_transfer order with `payment_status='pending'`
- **THEN** `payment_status` is set to `'paid'` and the `placed` email is queued

#### Scenario: Double-marking payment is rejected
- **WHEN** an admin sends `PATCH /v1/admin/orders/{id}/payment` for an order already at `payment_status='paid'`
- **THEN** the API returns HTTP 409

#### Scenario: Non-admin cannot mark payment received
- **WHEN** a non-admin session sends `PATCH /v1/admin/orders/{id}/payment`
- **THEN** the API returns HTTP 403

#### Scenario: Endpoint rejects non-bank-transfer orders
- **WHEN** an admin sends `PATCH /v1/admin/orders/{id}/payment` for a COD or card order
- **THEN** the API returns HTTP 422 indicating this endpoint is only for bank_transfer orders
