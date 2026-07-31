## ADDED Requirements

### Requirement: Product safety metadata exists for candle offers
The system SHALL support product-specific safety metadata for candle offers, including localized safety warnings and localized care/use instructions. Existing product IDs SHALL be treated as the public product identifier unless a later change introduces a separate SKU field.

#### Scenario: Product has safety metadata
- **WHEN** a product is created or updated with safety warnings and care instructions
- **THEN** the system stores the localized safety metadata and returns it through admin product responses

#### Scenario: Existing products remain valid
- **WHEN** the migration runs on products that do not yet have safety metadata
- **THEN** existing products remain readable and editable without data loss

### Requirement: Responsible party information is available on product offers
The system SHALL make trader/manufacturer or EU responsible-person information available on online product offers using the centralized legal identity source.

#### Scenario: Product offer shows responsible party
- **WHEN** a customer views a product detail page
- **THEN** the page can show the responsible party name, geographic address, and contact email from the centralized legal identity source

### Requirement: Candle safety information is not hidden only in FAQ
Safety warnings and care/use information SHALL be available on product detail pages and SHALL NOT rely solely on FAQ content.

#### Scenario: Product detail contains safety section
- **WHEN** a product has safety warnings or care instructions
- **THEN** the product detail page displays them in a product-specific safety section
