## ADDED Requirements

### Requirement: Admin product schema includes shipping weight
The admin product schema SHALL include a `weight_grams` integer field representing the product's shipping weight (product plus its container). `CreateProductRequest`, `UpdateProductRequest`, and the admin product response SHALL expose `weight_grams`. When not supplied on creation, `weight_grams` SHALL default to 300. This field SHALL NOT appear in the public product API response — it is a shipping input only.

#### Scenario: Create product without weight uses default
- **WHEN** admin POSTs a product without a `weight_grams` value
- **THEN** the product is created with `weight_grams` = 300

#### Scenario: Create product with explicit weight
- **WHEN** admin POSTs a product with `weight_grams` = 550
- **THEN** the product is persisted with `weight_grams` = 550
- **AND** the admin product response includes `weight_grams` = 550

#### Scenario: Update product weight
- **WHEN** admin PATCHes `weight_grams` = 420 for an existing product
- **THEN** the product's stored `weight_grams` becomes 420

#### Scenario: Public API excludes weight
- **WHEN** a public client GETs a product via `/v1/products/{id}`
- **THEN** the response does NOT include a `weight_grams` field

## MODIFIED Requirements

### Requirement: CSV import supports dual-language columns
The `POST /v1/admin/products/import` endpoint SHALL accept CSV files with columns `name_en`, `name_bg`, `description_en`, `description_bg`. The `name_en` column is required; BG columns are optional. The endpoint SHALL additionally accept the optional columns `weight_grams`, `is_featured`, `materials`, `days_to_craft`, and `is_active`; when a column is absent the field's normal default applies (`weight_grams` defaults to 300, `is_active` to true, `is_featured` to false).

#### Scenario: Import CSV with both languages
- **WHEN** admin uploads a CSV with `name_en`, `name_bg`, `description_en`, `description_bg` columns
- **THEN** products are created/upserted with content in both languages

#### Scenario: Import CSV with English only
- **WHEN** admin uploads a CSV with only `name_en` and `description_en` columns
- **THEN** products are created with BG fields as NULL

#### Scenario: Import CSV with extended optional columns
- **WHEN** admin uploads a CSV that includes `weight_grams`, `is_featured`, `materials`, `days_to_craft`, and `is_active` columns
- **THEN** those values are applied to the upserted products

#### Scenario: Import CSV omitting weight applies default
- **WHEN** admin uploads a CSV without a `weight_grams` column
- **THEN** upserted products receive `weight_grams` = 300
