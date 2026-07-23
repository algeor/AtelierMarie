## ADDED Requirements

### Requirement: Category dropdown sourced from managed categories
The admin product form's category dropdown SHALL be populated from `GET /v1/categories` (active categories) rather than a hardcoded frontend constant. Options SHALL display the localized category name and submit the category slug. An admin management page SHALL allow creating, renaming, reordering, activating/deactivating, and deleting categories, reachable from the admin sidebar.

#### Scenario: Form dropdown lists managed categories
- **WHEN** the admin opens the product create/edit form
- **THEN** the category dropdown lists active categories fetched from the API, showing localized names and submitting slugs

#### Scenario: Newly created category appears in the form
- **WHEN** an admin adds a category on the management page and then opens the product form
- **THEN** the new category appears as a selectable option without a code change

#### Scenario: Manage categories from the sidebar
- **WHEN** an admin navigates to the categories management page
- **THEN** they can create, rename, reorder, deactivate, and (when unused) delete categories
