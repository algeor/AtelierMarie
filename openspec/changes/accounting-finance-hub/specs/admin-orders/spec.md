## ADDED Requirements

### Requirement: Admin order accounting readiness fields
Admin order list and detail responses SHALL include accounting readiness fields: finance period id when assigned, accounting classification state, document reference status, payment reconciliation status, payout reconciliation status when applicable, COD settlement status when applicable, blocking exception count, and link metadata for the Accounting & Finance Hub.

#### Scenario: Admin order list shows accounting flags
- **WHEN** an admin lists orders that include a paid card order missing payout reconciliation and a COD order missing settlement
- **THEN** each order row includes accounting readiness fields showing the relevant reconciliation status and exception count

### Requirement: Admin order document references
Admin order detail SHALL allow admins to add, edit, and view accounting document references linked to the order, including invoice number, credit note number, fiscal receipt reference, external source system, issue date, totals, status, and notes. Every change SHALL write a finance audit event.

#### Scenario: Admin records fiscal receipt reference
- **WHEN** an admin adds a fiscal receipt reference to an order detail page
- **THEN** the order detail response includes the reference and the document ledger includes the linked document row

#### Scenario: Document reference edit is audited
- **WHEN** an admin edits an invoice reference on an order
- **THEN** the system records a finance audit event with actor, timestamp, old value, new value, and linked order id

### Requirement: Admin order accounting filters
`GET /v1/admin/orders` SHALL support accounting-oriented filters for missing document reference, unresolved finance exception, payout mismatch, COD settlement pending, refund document missing, VAT review required, and finance period id.

#### Scenario: Filter orders missing document reference
- **WHEN** an admin requests `GET /v1/admin/orders?accounting_filter=missing_document_reference`
- **THEN** the response contains only orders that currently have a missing required accounting document reference

### Requirement: Admin order links to finance hub
Admin order detail SHALL include a link target to the relevant finance period, ledger rows, document ledger entries, and exceptions when accounting data exists for the order.

#### Scenario: Order detail links to exception
- **WHEN** an order has a blocking finance exception
- **THEN** admin order detail includes a finance hub link that opens the exception context for that order
