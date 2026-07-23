## ADDED Requirements

### Requirement: Category filter pills display localized names
The storefront category filter pills SHALL derive available category slugs from the loaded products and display each slug's localized name from the products' `category_name` metadata, while continuing to filter by slug. The existing pill behavior (All-first, hide when fewer than 2, empty-state message) is unchanged.

#### Scenario: Pills show localized names
- **WHEN** the /products page loads in Bulgarian and products reference slug "floral"
- **THEN** the pill displays the product response's Bulgarian `category_name` for "floral" (or English fallback if BG is NULL) while filtering by the slug

#### Scenario: Inactive referenced category still displays label
- **WHEN** the /products page includes a product assigned to inactive category slug "retired"
- **THEN** a pill for "retired" displays the resolved `category_name` from that product response
- **AND** filtering still matches by the stored slug

#### Scenario: Filtering still keyed by slug
- **WHEN** a user clicks a localized category pill
- **THEN** the grid filters to products whose `category` slug matches that pill
