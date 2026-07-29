## ADDED Requirements

### Requirement: Public product responses include safety metadata
Public product list and detail responses SHALL include localized safety warning and care instruction fields needed by the storefront. The fields SHALL resolve according to the requested locale with fallback behavior consistent with product name/description localization.

#### Scenario: Detail response includes localized safety metadata
- **WHEN** `GET /v1/products/{id}?locale=bg` is called for a product with Bulgarian safety metadata
- **THEN** the response includes Bulgarian safety warnings and care instructions

#### Scenario: Safety metadata falls back to English
- **WHEN** `GET /v1/products/{id}?locale=bg` is called and Bulgarian safety metadata is empty
- **THEN** the response falls back to English safety metadata when available

#### Scenario: List response includes safety metadata without admin-only fields
- **WHEN** `GET /v1/products` is called
- **THEN** each public product may include resolved safety metadata
- **AND** the response does not expose admin-only translation staleness fields
