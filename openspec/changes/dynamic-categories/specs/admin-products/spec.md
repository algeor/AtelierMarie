## ADDED Requirements

### Requirement: Category dropdown sourced from managed categories
The admin product form's category dropdown SHALL be populated from managed category API data rather than a hardcoded frontend constant. Create mode SHALL present active categories as assignable options. Edit mode SHALL include the product's current category even if inactive, marked as retired, while preventing assignment to other inactive categories. Options SHALL display the localized category name and submit the category slug. An admin management page SHALL allow creating, renaming, reordering, activating/deactivating, and deleting categories, reachable from the admin sidebar.

#### Scenario: Form dropdown lists managed categories
- **WHEN** the admin opens the product create/edit form
- **THEN** the category dropdown lists managed categories fetched from the API, showing localized names and submitting slugs
- **AND** inactive categories are not assignable except for the product's current inactive category in edit mode

#### Scenario: Newly created category appears in the form
- **WHEN** an admin adds a category on the management page and then opens the product form
- **THEN** the new category appears as a selectable option without a code change

#### Scenario: Existing inactive category can be preserved on edit
- **WHEN** an admin edits a product whose current category has been deactivated
- **THEN** the form shows that category with a retired/inactive label
- **AND** submitting unrelated changes preserves the existing category instead of failing validation

#### Scenario: Manage categories from the sidebar
- **WHEN** an admin navigates to the categories management page
- **THEN** they can create, rename, reorder, deactivate, and (when unused) delete categories
