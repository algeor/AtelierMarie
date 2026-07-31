## ADDED Requirements

### Requirement: Product detail renders safety and responsible-party information
The product detail page SHALL render a product safety section containing localized safety warnings, care/use instructions, product identifier, and responsible-party/trader information when available.

#### Scenario: Safety section renders on product detail
- **WHEN** a product detail page receives product safety warnings or care instructions
- **THEN** it displays them in a visible product safety section

#### Scenario: Product identifier renders
- **WHEN** a product detail page renders
- **THEN** it shows or makes available the product identifier using the product ID unless a separate SKU exists

#### Scenario: Responsible party renders
- **WHEN** legal identity values are configured
- **THEN** the product detail page displays the responsible-party or trader name, geographic address, and contact email in the safety/legal section

### Requirement: Product detail safety section is accessible and localized
The safety section SHALL use localized headings and copy and SHALL remain readable on mobile and desktop layouts.

#### Scenario: Bulgarian safety section renders localized labels
- **WHEN** a Bulgarian product detail page renders safety metadata
- **THEN** the safety section uses Bulgarian labels and text where available
