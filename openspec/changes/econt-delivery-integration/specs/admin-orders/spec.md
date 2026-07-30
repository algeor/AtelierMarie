## ADDED Requirements

### Requirement: Admin order detail exposes Econt fulfillment panel
Admin order detail SHALL show an Econt fulfillment panel for Econt orders. The panel SHALL display configuration readiness, delivery validation state, courier sync status, shipment number, label PDF link, last error, and available actions.

#### Scenario: Econt order ready for label
- **WHEN** an admin views a confirmed Econt order with valid settings and no label
- **THEN** the panel shows a primary action to create an Econt label/AWB

#### Scenario: Econt label created
- **WHEN** an admin views an Econt order with a shipment number and label URL
- **THEN** the panel shows shipment number, tracking link, label PDF action, refresh trace action, and safe delete availability if applicable

#### Scenario: Non-Econt order
- **WHEN** an admin views a Speedy order
- **THEN** the Econt panel is hidden or shows that the order is not eligible for Econt fulfillment

### Requirement: Admin can repair Econt delivery data before label creation
The admin order detail SHALL allow an admin to repair missing or invalid Econt fulfillment fields before label creation, including office code, recipient phone, package count, shipment description, and payment-side override where allowed.

#### Scenario: Missing office code repair
- **WHEN** an Econt office order lacks `office_code`
- **THEN** the admin panel offers a way to reselect or enter a valid Econt office code before creating a label

#### Scenario: Package count override
- **WHEN** an admin changes package count before AWB creation
- **THEN** the next Econt payload uses the overridden package count

### Requirement: Admin actions show safe loading and errors
Econt admin actions SHALL show loading state, prevent duplicate submissions, and display actionable errors without exposing secrets or raw stack traces.

#### Scenario: Create label in progress
- **WHEN** an admin clicks create label
- **THEN** the button is disabled until the request completes

#### Scenario: Econt validation error
- **WHEN** Econt rejects a payload due to invalid delivery data
- **THEN** the admin sees a concise validation message and the failed action is recorded for audit
