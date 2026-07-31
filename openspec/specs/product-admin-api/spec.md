## Purpose

Defines admin product API behavior for product creation, updates, import, metadata, safety, and admin-only product fields.

## Requirements
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

#### Scenario: Import CSV omitting weight applies default to new products
- **WHEN** admin uploads a CSV without a `weight_grams` column that creates new products
- **THEN** the newly-created products receive `weight_grams` = 300 (DB default)

#### Scenario: Import CSV omitting weight preserves existing product weight
- **WHEN** admin uploads a CSV without a `weight_grams` column that upserts an existing product
- **THEN** that product's current `weight_grams` is left unchanged (not reset to 300)

### Requirement: Admin product response exposes the image gallery
The admin product response SHALL include the ordered `images` array (id, image_url, thumbnail_url, sort_order, is_primary) and `primary_image_url`, replacing the single `image_url` field, so the admin UI can manage the gallery.

#### Scenario: Admin detail includes images
- **WHEN** an admin fetches a product via the admin endpoint
- **THEN** the response includes the ordered `images` array with the primary flagged

### Requirement: Admin product schema includes discount fields
`CreateProductRequest`, `UpdateProductRequest`, and the admin product response SHALL expose raw discount configuration fields: `discount_percent`, `discount_starts_at`, and `discount_ends_at`. The admin response SHALL additionally include the computed `effective_price_cents` and `discount_active` so the admin UI can preview the live sale price. Datetime inputs SHALL be normalized to canonical UTC text before persistence. Validation (percent 1–99, start < end, percent required when a date is set) SHALL be enforced server-side. Partial updates SHALL be validated after merging submitted discount fields with the existing persisted discount fields.

#### Scenario: Create product with a manual discount
- **WHEN** admin POSTs a product with `discount_percent` = 15 and no dates
- **THEN** the product is created with the discount and the admin response reports `discount_active` = true and the discounted `effective_price_cents`

#### Scenario: Create product with a scheduled discount
- **WHEN** admin POSTs a product with `discount_percent` = 25, `discount_starts_at` and `discount_ends_at` set in the future
- **THEN** the product is created and the admin response reports `discount_active` = false until the window opens

#### Scenario: Clear a discount via update
- **WHEN** admin updates `discount_percent` = null on a discounted product
- **THEN** `discount_percent`, `discount_starts_at`, and `discount_ends_at` are cleared, and `effective_price_cents` reverts to `price_cents`

#### Scenario: Update one bound on existing scheduled discount
- **WHEN** a product already has `discount_percent` = 20 and an admin updates only `discount_ends_at` to a later valid datetime
- **THEN** the update succeeds because validation uses the merged persisted discount fields

#### Scenario: Reject date-only update without resulting percent
- **WHEN** a product has no discount and an admin updates only `discount_starts_at`
- **THEN** the request is rejected with a validation error because the resulting discount has a date without a percent

#### Scenario: Reject invalid discount on update
- **WHEN** admin updates `discount_percent` = 150
- **THEN** the request is rejected with a validation error

### Requirement: Bulk product discount endpoint
The system SHALL expose `PATCH /v1/admin/products/bulk-discount` for admins to apply or remove the existing product discount fields on multiple products. The request SHALL specify `operation` as `apply` or `remove`, and SHALL specify exactly one target source: an explicit `product_ids` list or an admin product-list `filter` descriptor. The endpoint SHALL reject requests with both target sources, no target source, an empty resolved target set, or more than 500 resolved targets before applying any changes.

For `operation = apply`, the request SHALL include the same discount payload fields used by single-product updates: `discount_percent`, `discount_starts_at`, and `discount_ends_at`. Validation and datetime normalization SHALL reuse the same product service discount write logic as `PATCH /v1/admin/products/{product_id}`. For `operation = remove`, the endpoint SHALL clear `discount_percent`, `discount_starts_at`, and `discount_ends_at` on every successful target, using the same clear-stale-window behavior as the single-product update path.

After request-level validation succeeds, the endpoint SHALL process targets in one transaction with per-product savepoints. A per-product failure SHALL roll back only that product's savepoint and SHALL NOT roll back successful updates for other targets. The response SHALL include `success_count`, `failure_count`, and a `results` list with one item per resolved target: `{id, status, error?}` where `status` is `updated`, `skipped`, or `failed`.

#### Scenario: Apply discount to explicit products
- **WHEN** an admin sends `PATCH /v1/admin/products/bulk-discount` with `operation = apply`, `product_ids = ["a", "b"]`, and `discount_percent = 20`
- **THEN** products `a` and `b` are updated using the same discount validation and normalization logic as single-product update
- **AND** the response reports two updated results

#### Scenario: Remove discount from explicit products
- **WHEN** an admin sends `operation = remove` with `product_ids = ["a", "b"]`
- **THEN** each successful target has `discount_percent`, `discount_starts_at`, and `discount_ends_at` stored as NULL

#### Scenario: Apply discount to all products matching filters
- **WHEN** an admin sends `operation = apply` with a filter descriptor for active products in category `spring` and `discount_percent = 15`
- **THEN** the server resolves all matching admin-list products without page/limit pagination
- **AND** applies the discount to every resolved target up to the 500-product cap

#### Scenario: Reject ambiguous targets
- **WHEN** a request includes both `product_ids` and `filter`
- **THEN** the endpoint rejects the request with a validation error before applying changes

#### Scenario: Reject too many resolved targets
- **WHEN** a filter descriptor resolves to more than 500 products
- **THEN** the endpoint rejects the request with error code `BULK_TARGET_LIMIT_EXCEEDED`
- **AND** no product is changed

#### Scenario: Per-product failure is reported
- **WHEN** a bulk request targets products `a`, `missing`, and `b`
- **THEN** products `a` and `b` are updated successfully
- **AND** the result for `missing` has `status = failed` and an error explaining that the product was not found

#### Scenario: Invalid apply payload changes nothing
- **WHEN** an admin sends `operation = apply` with `discount_percent = 100`
- **THEN** the endpoint rejects the request before processing targets
- **AND** no product is changed

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
