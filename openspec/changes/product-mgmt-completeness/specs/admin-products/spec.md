## MODIFIED Requirements

### Requirement: Product create/edit form
The system SHALL provide a form at `/admin/products/new` (create) and `/admin/products/[id]/edit` (edit) with fields: name, description, price (EUR input converted to cents), category (dropdown), stock (number), weight (grams, number), image URL, is_featured (checkbox), and is_active (toggle). The weight field SHALL default to 300 grams for new products. The is_active toggle SHALL let admins set active/inactive state directly while editing, in addition to the list-table toggle.

#### Scenario: Create a new product
- **WHEN** admin fills in the product form with valid data and submits
- **THEN** the product is created via the API
- **AND** admin is redirected to `/admin/products`
- **AND** a success message is displayed

#### Scenario: Edit an existing product
- **WHEN** admin navigates to `/admin/products/[id]/edit`
- **THEN** the form is pre-filled with the product's current data, including weight and active state
- **AND** admin can modify fields and submit to update

#### Scenario: Form validation
- **WHEN** admin submits the form with missing required fields (name, price, category)
- **THEN** validation errors are shown inline next to the relevant fields
- **AND** the form is NOT submitted

#### Scenario: Price input in EUR displayed, stored as cents
- **WHEN** admin enters "32.50" in the price field
- **THEN** the value is stored as 3250 (cents) when submitted to the API

#### Scenario: Weight defaults to 300 grams for new products
- **WHEN** admin opens the create form
- **THEN** the weight field is pre-populated with 300 grams

#### Scenario: Toggle active state while editing
- **WHEN** admin flips the is_active toggle off and submits the edit form
- **THEN** the product is updated to inactive without needing the list-table action
