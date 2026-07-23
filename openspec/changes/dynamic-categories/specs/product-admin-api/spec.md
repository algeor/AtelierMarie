## ADDED Requirements

### Requirement: Product category validated against managed categories
Product create and update SHALL validate that a supplied `category` is the slug of an existing **active** category, rejecting unknown or inactive slugs with a 422 validation error. A NULL/empty category remains allowed (uncategorized).

#### Scenario: Create with a valid category slug
- **WHEN** admin POSTs a product with `category` = "floral" and that active category exists
- **THEN** the product is created

#### Scenario: Reject unknown category
- **WHEN** admin POSTs a product with `category` = "not-a-real-category"
- **THEN** the request is rejected with a 422 validation error

#### Scenario: Uncategorized product allowed
- **WHEN** admin POSTs a product with no category
- **THEN** the product is created with `category` = NULL
