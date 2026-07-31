## ADDED Requirements

### Requirement: Checkout supports enhanced Econt office selection
The checkout UI SHALL support both the existing static Econt office picker and the optional Econt Office Locator iframe. In either mode, selecting an Econt office SHALL produce a delivery object containing the Econt office code.

#### Scenario: Static picker submits office code
- **WHEN** a customer selects an Econt office from the static picker
- **THEN** the checkout state includes `office_code` for order submission

#### Scenario: Office locator submits office code
- **WHEN** a customer selects an office in the Econt Office Locator iframe
- **THEN** the checkout state shows the selected office and includes the returned Econt `code`

### Requirement: Customer sees Econt shipment status after purchase
The order confirmation and order detail pages SHALL show Econt shipment number, label/tracking availability, and trace summary when available. Customers SHALL NOT see raw Econt errors or admin-only fulfillment controls.

#### Scenario: Econt shipment created
- **WHEN** an order has an Econt shipment number and tracking URL
- **THEN** customer order pages show the shipment number and tracking link

#### Scenario: Econt label not created yet
- **WHEN** an Econt order has no shipment number
- **THEN** customer order pages show normal order status without exposing internal fulfillment actions
