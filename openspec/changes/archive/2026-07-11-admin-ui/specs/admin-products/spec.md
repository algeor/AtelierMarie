## ADDED Requirements

### Requirement: Product list table
The admin product list at `/admin/products` SHALL display all products in a table with columns: Name, Category, Price, Stock, Status (active/inactive), and Actions (edit, deactivate/activate).

#### Scenario: Product table renders
- **WHEN** admin navigates to `/admin/products`
- **THEN** a table displays all products with columns: Name, Category, Price, Stock, Status, Actions

#### Scenario: Product table shows formatted data
- **WHEN** the product table renders
- **THEN** prices are displayed in EUR format (e.g., "EUR 32.00")
- **AND** status shows "Active" or "Inactive" with appropriate badge color
- **AND** stock shows the numeric quantity

### Requirement: Product deactivate/activate action
The system SHALL allow admins to toggle a product's active status directly from the product list table.

#### Scenario: Deactivate an active product
- **WHEN** admin clicks "Deactivate" action on an active product
- **THEN** the product's status changes to inactive
- **AND** the table row updates to show "Inactive" status
- **AND** the action button changes to "Activate"

#### Scenario: Activate an inactive product
- **WHEN** admin clicks "Activate" action on an inactive product
- **THEN** the product's status changes to active
- **AND** the table row updates to show "Active" status

### Requirement: Create product button
The product list SHALL include a "Create Product" button that navigates to the product creation form.

#### Scenario: Navigate to create product form
- **WHEN** admin clicks "Create Product" button
- **THEN** the browser navigates to `/admin/products/new`

### Requirement: Product create/edit form
The system SHALL provide a form at `/admin/products/new` (create) and `/admin/products/[id]/edit` (edit) with fields: name, description, price (EUR input converted to cents), category (dropdown), stock (number), image URL, is_featured (checkbox).

#### Scenario: Create a new product
- **WHEN** admin fills in the product form with valid data and submits
- **THEN** the product is created via the API
- **AND** admin is redirected to `/admin/products`
- **AND** a success message is displayed

#### Scenario: Edit an existing product
- **WHEN** admin navigates to `/admin/products/[id]/edit`
- **THEN** the form is pre-filled with the product's current data
- **AND** admin can modify fields and submit to update

#### Scenario: Form validation
- **WHEN** admin submits the form with missing required fields (name, price, category)
- **THEN** validation errors are shown inline next to the relevant fields
- **AND** the form is NOT submitted

#### Scenario: Price input in EUR displayed, stored as cents
- **WHEN** admin enters "32.50" in the price field
- **THEN** the value is stored as 3250 (cents) when submitted to the API
