## ADDED Requirements

### Requirement: Product detail category badge shows localized name
The product detail page category badge SHALL display the category's localized name resolved from the managed categories (slug → `name` for the active locale, fallback to `name_en`), instead of the raw stored slug.

#### Scenario: Badge shows localized name
- **WHEN** the detail page renders in English for a product with `category` = "floral"
- **THEN** the badge shows "Floral" (the category's `name_en`), not the raw slug

#### Scenario: Uncategorized product shows no badge
- **WHEN** the detail page renders for a product with `category` = NULL
- **THEN** no category badge is shown
