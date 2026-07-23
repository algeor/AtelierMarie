## ADDED Requirements

### Requirement: Product detail category badge shows localized name
The product detail page category badge SHALL display the product response's localized `category_name` instead of the raw stored slug. The stored `category` slug remains available for filtering/linking behavior.

#### Scenario: Badge shows localized name
- **WHEN** the detail page renders in English for a product with `category` = "floral"
- **THEN** the badge shows the response `category_name` "Floral", not the raw slug

#### Scenario: Badge shows inactive category name
- **WHEN** the detail page renders for a product assigned to an inactive category
- **THEN** the badge still shows the response `category_name`

#### Scenario: Uncategorized product shows no badge
- **WHEN** the detail page renders for a product with `category` = NULL
- **THEN** no category badge is shown
