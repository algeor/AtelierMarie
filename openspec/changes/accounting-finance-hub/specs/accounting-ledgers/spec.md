## ADDED Requirements

### Requirement: Sales ledger
The system SHALL provide an admin-only sales ledger for a selected period. Each row SHALL represent an order line, shipping line, discount allocation, return/sales reversal, or adjustment needed for accounting. Sales ledger rows SHALL include order id, order number, order date, customer country, delivery country, item/product snapshot, SKU/product id when available, quantity, unit amount, discount amount, net amount, VAT/tax rate, VAT/tax amount, gross amount, currency, payment method, document reference status, and source row identifiers.

#### Scenario: Order line appears in sales ledger
- **WHEN** a paid order line belongs to the selected period by order date
- **THEN** the sales ledger includes one row with the checkout-time product name, quantity, unit amount, discount amount, tax fields, gross amount, currency, and order number

#### Scenario: Return creates reversal row
- **WHEN** a return/refund reverses an order line in the selected period
- **THEN** the sales ledger includes a negative reversal row linked to the original order and return/refund record

### Requirement: Payment and refund ledger
The system SHALL provide a payment ledger for card payments, pay-on-delivery collections, manual payment events, refunds, disputes, failed payments, and review-required payment events. Rows SHALL include event date, order id, order number, provider, payment method, provider payment/refund/dispute ids, gross amount, fee amount when known, net amount when known, currency, status, source event id, and reconciliation status.

#### Scenario: Stripe payment appears with provider ids
- **WHEN** a Stripe card payment is confirmed for an order
- **THEN** the payment ledger includes the Stripe PaymentIntent or charge id, order number, gross amount, currency, status, and source payment event id

#### Scenario: Refund appears separately from sale
- **WHEN** a Stripe refund is created or confirmed
- **THEN** the payment ledger includes a refund row linked to the original order and refund record without mutating the original payment row

### Requirement: Stripe payout and fee ledger
The system SHALL store and expose Stripe balance/payout activity imported from the Stripe API/reporting data or manual CSV fallback. Payout ledger rows SHALL include balance transaction id, reporting category, created date, available/effective/arrival date, gross amount, fee amount, net amount, currency, payment intent/charge/refund ids when present, payout id, payout status, trace id, and match status.

#### Scenario: Stripe payout import stores fees and net amount
- **WHEN** Stripe balance data contains a charge with gross, fee, net, payment intent id, and payout id
- **THEN** the system stores a payout ledger row that preserves all provider ids, gross amount, fee amount, net amount, currency, and payout id

#### Scenario: Payout mismatch creates exception
- **WHEN** imported Stripe payout totals do not match matched payment/refund activity within the configured tolerance
- **THEN** the system marks the payout as mismatched and creates an accounting exception linked to the payout

### Requirement: COD and courier settlement ledger
The system SHALL provide COD and courier settlement ledger rows for delivered pay-on-delivery orders, courier collection evidence, explicit settlement records, courier return fees, courier claim amounts, and settlement mismatches. The ledger SHALL reuse existing COD settlement and courier claim report data where available.

#### Scenario: Delivered COD order without settlement is listed
- **WHEN** a payment-on-delivery order is delivered and has no settlement record
- **THEN** the COD ledger includes the order with state `unsettled` and creates a review exception

#### Scenario: Econt COD evidence is preserved separately
- **WHEN** Econt trace evidence contains collected or paid COD amounts
- **THEN** the COD ledger displays the evidence fields separately from the explicit admin settlement record

### Requirement: Accounting document ledger
The system SHALL provide an accounting document ledger for invoices, credit notes, fiscal receipt references, alternative sales-registration document references, accountant-supplied documents, and external fiscal/accounting system documents. Rows SHALL include document type, document number, source system, issue date, linked order/refund/period, currency, net amount, tax amount, gross amount, status, file reference when available, and notes.

#### Scenario: External invoice reference appears in ledger
- **WHEN** an admin records an external invoice number for an order
- **THEN** the document ledger includes the document type, number, source system, issue date, linked order number, totals, status, and audit metadata

#### Scenario: Credit note references original document
- **WHEN** a credit note reference is recorded for a refund
- **THEN** the document ledger requires and stores an unambiguous reference to the original invoice or fiscal document being corrected

### Requirement: Ledger date basis
The system SHALL allow admins to filter ledger views by the appropriate date basis for each ledger: order date for sales, payment/refund event date for payments, payout effective/arrival date for provider payouts, settlement date for COD/courier settlements, and issue date for documents.

#### Scenario: Payment date differs from order date
- **WHEN** an order is placed in one month and paid in the next month
- **THEN** the sales ledger can include it by order date while the payment ledger includes the payment by payment event date
