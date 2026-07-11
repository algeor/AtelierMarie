## MODIFIED Requirements

### Requirement: Create product endpoint
The system SHALL expose `POST /v1/admin/products` accepting product data with dual-language content fields: `name_en`, `name_bg`, `description_en`, `description_bg`. At minimum, `name_en` SHALL be required. The `name_bg` and `description_bg` fields are optional (fallback applies on display).

#### Scenario: Create product with both languages
- **WHEN** admin POSTs a product with `name_en`, `name_bg`, `description_en`, `description_bg`
- **THEN** the product is created with content in both languages and staleness flags set to false

#### Scenario: Create product with English only
- **WHEN** admin POSTs a product with only `name_en` and `description_en`
- **THEN** the product is created with BG fields as NULL; `translation_stale_bg` is set to false (nothing to be stale against)

### Requirement: Update product endpoint
The system SHALL expose `PATCH /v1/admin/products/{product_id}` accepting partial updates including dual-language content fields. When content in one language is updated, the system SHALL set the other language's staleness flag to true.

#### Scenario: Update English description flags Bulgarian as stale
- **WHEN** admin PATCHes `description_en` for a product
- **THEN** `translation_stale_bg` is set to true

#### Scenario: Update Bulgarian name flags English as stale
- **WHEN** admin PATCHes `name_bg` for a product
- **THEN** `translation_stale_en` is set to true

#### Scenario: Update Bulgarian content clears its staleness flag
- **WHEN** admin PATCHes `description_bg` for a product that has `translation_stale_bg = true`
- **THEN** `translation_stale_bg` is set to false

#### Scenario: Update both languages simultaneously
- **WHEN** admin PATCHes both `name_en` and `name_bg` in the same request
- **THEN** neither staleness flag is set (both sides updated together)

### Requirement: Product response includes staleness metadata for admin
The system SHALL include `translation_stale_en` and `translation_stale_bg` boolean fields in admin product responses (not in public API responses).

#### Scenario: Admin gets product with staleness info
- **WHEN** admin GETs a product via admin endpoint
- **THEN** the response includes `translation_stale_en` and `translation_stale_bg` fields

#### Scenario: Public API excludes staleness info
- **WHEN** a public client GETs a product via `/v1/products/{id}`
- **THEN** the response does NOT include staleness fields

### Requirement: CSV import supports dual-language columns
The `POST /v1/admin/products/import` endpoint SHALL accept CSV files with columns `name_en`, `name_bg`, `description_en`, `description_bg`. The `name_en` column is required; BG columns are optional.

#### Scenario: Import CSV with both languages
- **WHEN** admin uploads a CSV with `name_en`, `name_bg`, `description_en`, `description_bg` columns
- **THEN** products are created/upserted with content in both languages

#### Scenario: Import CSV with English only
- **WHEN** admin uploads a CSV with only `name_en` and `description_en` columns
- **THEN** products are created with BG fields as NULL
