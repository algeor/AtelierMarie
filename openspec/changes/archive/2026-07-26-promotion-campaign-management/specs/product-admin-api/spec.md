## ADDED Requirements

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
