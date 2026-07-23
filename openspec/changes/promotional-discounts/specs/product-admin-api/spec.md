## ADDED Requirements

### Requirement: Admin product schema includes discount fields
`CreateProductRequest`, `UpdateProductRequest`, and the admin product response SHALL expose `discount_percent`, `discount_starts_at`, and `discount_ends_at`. The admin response SHALL additionally include the computed `effective_price_cents` and `discount_active` so the admin UI can preview the live sale price. Validation (percent 1–99, start < end, percent required when a date is set) SHALL be enforced server-side.

#### Scenario: Create product with a manual discount
- **WHEN** admin POSTs a product with `discount_percent` = 15 and no dates
- **THEN** the product is created with the discount and the admin response reports `discount_active` = true and the discounted `effective_price_cents`

#### Scenario: Create product with a scheduled discount
- **WHEN** admin POSTs a product with `discount_percent` = 25, `discount_starts_at` and `discount_ends_at` set in the future
- **THEN** the product is created and the admin response reports `discount_active` = false until the window opens

#### Scenario: Clear a discount via update
- **WHEN** admin PATCHes `discount_percent` = null on a discounted product
- **THEN** the discount is removed and `effective_price_cents` reverts to `price_cents`

#### Scenario: Reject invalid discount on update
- **WHEN** admin PATCHes `discount_percent` = 150
- **THEN** the request is rejected with a validation error
