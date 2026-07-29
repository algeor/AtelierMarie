## ADDED Requirements

### Requirement: Admin product schema includes safety metadata fields
Admin product create, update, detail, list, and CSV import surfaces SHALL support localized product safety metadata fields: `safety_warnings_en`, `safety_warnings_bg`, `care_instructions_en`, and `care_instructions_bg`. The fields SHALL be optional, bounded in length, and preserved on partial updates unless explicitly changed.

#### Scenario: Create product with safety metadata
- **WHEN** an admin creates a product with English and Bulgarian safety warnings and care instructions
- **THEN** the product is persisted and the admin response includes the submitted safety metadata

#### Scenario: Partial update preserves safety metadata
- **WHEN** a product has safety metadata and an admin updates only stock
- **THEN** the safety metadata remains unchanged

#### Scenario: CSV import accepts safety metadata columns
- **WHEN** an admin imports CSV rows with safety warning and care instruction columns
- **THEN** the values are validated and stored for each imported product

### Requirement: Admin product form can edit safety metadata
The admin product UI SHALL expose text fields for the localized safety warning and care instruction fields and submit them through existing create/update flows.

#### Scenario: Product form submits safety metadata
- **WHEN** an admin fills safety metadata in the product form and saves
- **THEN** the submitted payload includes the safety metadata fields
