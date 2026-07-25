## ADDED Requirements

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
