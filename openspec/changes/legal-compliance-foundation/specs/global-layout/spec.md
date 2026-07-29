## ADDED Requirements

### Requirement: Footer includes legal policy links
The global storefront footer SHALL include localized links to Terms & Conditions, Privacy Policy, Cookie Policy, FAQ, Contact, and existing social links. The footer SHALL NOT add a standalone Returns link while returns are covered inside Terms & Conditions.

#### Scenario: Footer shows legal links
- **WHEN** the footer renders on a localized storefront page
- **THEN** Terms & Conditions, Privacy Policy, and Cookie Policy links are visible and navigable through localized routes

#### Scenario: Footer avoids obsolete returns and ODR links
- **WHEN** the footer renders
- **THEN** it does not show a standalone Returns link
- **AND** it does not include an outdated EU ODR platform link

### Requirement: Footer exposes quiet trader contact discoverability
The footer SHALL make legal/trader contact discoverable without turning the layout into a legal notice block.

#### Scenario: Trader contact remains discoverable
- **WHEN** a customer needs legal or order contact details
- **THEN** footer navigation provides access to Terms, Privacy, and Contact pages that contain the trader/contact information
