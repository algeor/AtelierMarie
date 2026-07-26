## ADDED Requirements

### Requirement: Product detail displays localized taxonomy metadata
The product detail page SHALL display localized product taxonomy metadata from the product response. Product type and category/tier MAY be displayed as badges. Labels SHALL be displayed as purpose/season/scent tags. Raw slugs SHALL NOT be displayed when localized names are available.

#### Scenario: Detail shows product type and category names
- **WHEN** the detail page renders in English for a product with `product_type` = "candles" and `category` = "medium"
- **THEN** the page shows localized names such as "Candles" and "Medium", not raw slugs

#### Scenario: Detail shows labels
- **WHEN** the detail page renders for a product assigned labels "winter" and "gift"
- **THEN** the page shows the localized label names as tags

#### Scenario: Detail shows inactive taxonomy names
- **WHEN** the detail page renders for a product assigned to an inactive label
- **THEN** the page still shows the response label name

#### Scenario: Product with no category tier shows no category badge
- **WHEN** the detail page renders for a product with `category` = NULL
- **THEN** no category/tier badge is shown
- **AND** product type and labels still render normally
