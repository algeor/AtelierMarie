## ADDED Requirements

### Requirement: Product category validated against managed categories
Product create SHALL validate that a supplied `category` is the slug of an existing **active** category, rejecting unknown or inactive slugs with a 422 validation error. Product update SHALL validate category reassignment the same way, while allowing omitted category values and allowing the product to keep its current inactive category. A NULL/empty category remains allowed (uncategorized).

#### Scenario: Create with a valid category slug
- **WHEN** admin POSTs a product with `category` = "floral" and that active category exists
- **THEN** the product is created

#### Scenario: Reject unknown category
- **WHEN** admin POSTs a product with `category` = "not-a-real-category"
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Reject assigning inactive category
- **WHEN** admin POSTs a product with `category` = "retired" and that category exists with `is_active` = 0
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Preserve existing inactive category on update
- **WHEN** a product already has `category` = "retired" and that category is inactive
- **AND** admin PATCHes another field without changing category, or submits the same current category slug
- **THEN** the product update succeeds and keeps `category` = "retired"

#### Scenario: Reject changing to a different inactive category
- **WHEN** admin PATCHes a product from `category` = "floral" to inactive `category` = "retired"
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Uncategorized product allowed
- **WHEN** admin POSTs a product with no category
- **THEN** the product is created with `category` = NULL

### Requirement: CSV import validates managed category slugs
CSV product import SHALL treat the `category` column as a category slug. Rows with non-empty category values SHALL validate against existing active category slugs and report row-level errors for unknown or inactive slugs. CSV import SHALL NOT auto-create categories.

#### Scenario: CSV row with active category slug imports
- **WHEN** admin imports a CSV row with `category` = "floral" and that category is active
- **THEN** the row is created or updated successfully

#### Scenario: CSV row with unknown category reports row error
- **WHEN** admin imports a CSV row with `category` = "new-family" and no active category exists for that slug
- **THEN** that row is skipped with a validation error
