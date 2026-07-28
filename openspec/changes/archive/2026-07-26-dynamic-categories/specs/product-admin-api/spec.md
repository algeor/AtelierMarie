## ADDED Requirements

### Requirement: Product taxonomy assignments validate against managed taxonomy
Product create SHALL validate that `product_type` is the slug of an existing active product type. Product create SHALL validate that supplied `category` is NULL/empty or an existing active category/tier slug. Product create SHALL validate that supplied labels are existing active label slugs. Product update SHALL validate reassignment the same way while allowing omitted taxonomy fields and allowing the product to keep its current inactive taxonomy assignments.

#### Scenario: Create candle with valid taxonomy
- **WHEN** admin POSTs a product with `product_type` = "candles", `category` = "medium", and labels `["winter", "gift"]`
- **THEN** the product is created with those taxonomy assignments

#### Scenario: Reject unknown product type
- **WHEN** admin POSTs a product with `product_type` = "not-a-real-type"
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Reject inactive category assignment
- **WHEN** admin POSTs a product with `category` = "retired" and that category exists with `is_active` = 0
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Reject unknown label assignment
- **WHEN** admin POSTs a product with labels `["winter", "unknown-label"]`
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Preserve current inactive taxonomy on update
- **WHEN** a product already has inactive label "retired"
- **AND** admin PATCHes another field without changing labels, or submits the same current label set
- **THEN** the product update succeeds and keeps the inactive label assignment

#### Scenario: Reject changing to a different inactive term
- **WHEN** admin PATCHes a product from category "medium" to inactive category "retired"
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Category tier may be unset
- **WHEN** admin POSTs a product with no category/tier
- **THEN** the product is created with `category` = NULL

### Requirement: CSV import validates managed taxonomy slugs
CSV product import SHALL treat taxonomy columns as slugs. Rows with non-empty taxonomy values SHALL validate against existing active taxonomy terms and report row-level errors for unknown or inactive terms. CSV import SHALL NOT auto-create product types, categories, or labels.

#### Scenario: CSV row with active taxonomy imports
- **WHEN** admin imports a CSV row with `product_type` = "candles", `category` = "small", and `labels` = "winter,gift"
- **THEN** the row is created or updated successfully

#### Scenario: CSV row with unknown taxonomy reports row error
- **WHEN** admin imports a CSV row with `product_type` = "new-family" and no active product type exists for that slug
- **THEN** that row is skipped with a validation error

#### Scenario: CSV import does not create labels
- **WHEN** admin imports a CSV row with `labels` = "brand-new-label" and no active label exists for that slug
- **THEN** that row is skipped with a validation error
- **AND** no label is auto-created
