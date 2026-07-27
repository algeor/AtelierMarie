## ADDED Requirements

### Requirement: Product form taxonomy controls are sourced from managed taxonomy
The admin product create/edit form SHALL populate product type, category/tier, and label controls from managed taxonomy API data rather than hardcoded frontend constants. Create mode SHALL present active product types, active categories/tiers, and active labels as assignable options. Edit mode SHALL include the product's current inactive taxonomy terms marked as retired, while preventing assignment to other inactive terms. Options SHALL display localized taxonomy names and submit slugs.

#### Scenario: Form lists managed taxonomy options
- **WHEN** the admin opens the product create/edit form
- **THEN** product type, category/tier, and label controls are fetched from admin taxonomy APIs
- **AND** options show localized names while submitting slugs
- **AND** inactive terms are not assignable except for current inactive terms in edit mode

#### Scenario: Newly created product type appears in form
- **WHEN** an admin creates product type "Boxes" in the taxonomy management view and then opens the product form
- **THEN** "Boxes" appears as a selectable product type without a code change

#### Scenario: Newly created label appears in form
- **WHEN** an admin creates label "Winter" in the taxonomy management view and then opens the product form
- **THEN** "Winter" appears as a selectable label without a code change

#### Scenario: Existing inactive taxonomy can be preserved on edit
- **WHEN** an admin edits a product whose current label has been deactivated
- **THEN** the form shows that label with a retired/inactive marker
- **AND** submitting unrelated changes preserves the existing label instead of failing validation

### Requirement: Dedicated taxonomy management views are reachable from admin navigation
The admin UI SHALL provide dedicated management views for product types, categories/tiers, and labels, reachable from the admin sidebar. Admins SHALL be able to create, rename, reorder, activate/deactivate, and delete unused terms from these views.

#### Scenario: Manage product types from sidebar
- **WHEN** an admin navigates to the product types management view
- **THEN** they can create, rename, reorder, deactivate, and delete unused product types

#### Scenario: Manage categories from sidebar
- **WHEN** an admin navigates to the categories/tiers management view
- **THEN** they can create, rename, reorder, deactivate, and delete unused categories/tiers

#### Scenario: Manage labels from sidebar
- **WHEN** an admin navigates to the labels management view
- **THEN** they can create, rename, reorder, deactivate, and delete unused labels

#### Scenario: Delete in-use term shows guidance
- **WHEN** an admin attempts to delete a taxonomy term that products still reference
- **THEN** the UI shows the 409 guidance from the API and suggests reassigning or deactivating the term
