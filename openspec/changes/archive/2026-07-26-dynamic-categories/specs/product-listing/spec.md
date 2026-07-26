## MODIFIED Requirements

### Requirement: Product listing uses sidebar faceted filters
The storefront product listing SHALL provide a faceted filter menu for product type, category/tier, and labels. Desktop layouts SHALL show filters in a side menu. Mobile layouts SHALL provide a collapsible filter panel. Filtering SHALL continue to update the product grid without a full page reload.

#### Scenario: Sidebar shows taxonomy filter groups
- **WHEN** the /products page loads
- **THEN** the filter menu shows groups for Product Type, Category, and Labels using localized taxonomy names from the public taxonomy endpoint

#### Scenario: Product types include admin-created values
- **WHEN** an admin creates active product type "Boxes"
- **THEN** "Boxes" appears in the Product Type filter group without a frontend code change

#### Scenario: Labels include admin-created values
- **WHEN** an admin creates active label "Winter"
- **THEN** "Winter" appears in the Labels filter group without a frontend code change

#### Scenario: Inactive taxonomy hidden from filter menu
- **WHEN** a taxonomy term is inactive
- **THEN** it is not shown as a public filter option
- **AND** products that already reference it still display its label metadata on product cards or detail views where applicable

### Requirement: Faceted filtering combines selected slugs
The product listing SHALL filter by taxonomy slugs while displaying localized taxonomy names. Users SHALL be able to combine product type, category/tier, and label filters.

#### Scenario: Filter by product type
- **WHEN** a user selects "Candles"
- **THEN** the grid shows only products whose product type slug is "candles"

#### Scenario: Filter by category tier
- **WHEN** a user selects "Premium"
- **THEN** the grid shows only products whose category/tier slug is "premium"

#### Scenario: Filter by label
- **WHEN** a user selects "Winter"
- **THEN** the grid shows only products assigned the "winter" label

#### Scenario: Combine filters
- **WHEN** a user selects Product Type "Boxes", Category "Premium", and Label "Gift"
- **THEN** the grid shows only products matching all selected filters

#### Scenario: Selected filters display as removable chips
- **WHEN** filters are active
- **THEN** selected filters appear above the grid as localized removable chips
- **AND** removing a chip updates the grid

#### Scenario: Empty filtered state
- **WHEN** no products match the selected filters
- **THEN** a friendly empty state message displays

#### Scenario: Filter results announced to screen readers
- **WHEN** any facet filter is applied or removed
- **THEN** a visually-hidden `<div aria-live="polite" role="status">` updates with the result count
