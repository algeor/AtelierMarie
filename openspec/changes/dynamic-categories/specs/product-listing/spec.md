## ADDED Requirements

### Requirement: Category filter pills display localized names
The storefront category filter pills SHALL display each category's localized name resolved from the managed categories (slug → `name` for the active locale, falling back to `name_en`), while continuing to filter by slug. The existing pill behavior (All-first, hide when fewer than 2, empty-state message) is unchanged.

#### Scenario: Pills show localized names
- **WHEN** the /products page loads in Bulgarian and products reference slug "floral"
- **THEN** the pill displays the Bulgarian `name_bg` for "floral" (or `name_en` if BG is NULL) while filtering by the slug

#### Scenario: Filtering still keyed by slug
- **WHEN** a user clicks a localized category pill
- **THEN** the grid filters to products whose `category` slug matches that pill
