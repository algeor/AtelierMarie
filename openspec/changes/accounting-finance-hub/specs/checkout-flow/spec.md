## ADDED Requirements

### Requirement: Optional invoice and business customer fields
`POST /v1/orders` SHALL accept an optional `invoice_profile` object for customers who request invoice/business document handling. The object SHALL support customer type (`individual` or `business`), legal name, VAT identification number, business registration number, billing address, billing country, invoice email, and optional purchase/reference note. Fields SHALL be validated for length and format and stored only when provided.

#### Scenario: Business invoice profile accepted
- **WHEN** a checkout request includes a valid business `invoice_profile` with legal name, VAT ID, billing country, billing address, and invoice email
- **THEN** the created order stores the invoice profile snapshot and returns that invoice profile in admin order detail responses

#### Scenario: Invalid invoice email rejected
- **WHEN** a checkout request includes `invoice_profile.invoice_email` with an invalid email format
- **THEN** the API returns HTTP 422 and no order is created

### Requirement: Accounting snapshot captured at checkout
`POST /v1/orders` SHALL snapshot accounting-relevant order data at checkout, including currency, item names, product ids, quantities, effective prices, discounts, shipping amount, delivery country, customer country when available, selected payment method, seller legal profile version when configured, VAT/fiscal settings version when configured, and invoice profile snapshot when provided.

#### Scenario: Order stores accounting settings versions
- **WHEN** an order is created while reviewed seller legal profile and VAT/fiscal settings exist
- **THEN** the order stores references to the effective settings versions used for accounting exports

#### Scenario: Missing settings does not block checkout
- **WHEN** seller legal profile or VAT/fiscal settings are incomplete during checkout
- **THEN** checkout can still create the order, and the accounting exception queue later flags the missing setup for period close

### Requirement: VAT classification state on checkout orders
Checkout SHALL assign an initial accounting classification state to each order: `unreviewed`, `domestic_default`, `business_vat_id_provided`, `cross_border_candidate`, or `manual_review_required`. The classification SHALL be based only on configured rules and captured customer/delivery data and SHALL NOT be presented as final tax advice.

#### Scenario: Cross-border customer creates review state
- **WHEN** a checkout order has a delivery country different from the seller country
- **THEN** the order receives a VAT classification state that marks it for accounting review or configured cross-border treatment
