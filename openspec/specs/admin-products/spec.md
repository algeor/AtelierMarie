## Requirements

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

### Requirement: Product form manages multiple images
The admin product create/edit form SHALL let admins upload up to 6 images, reorder them, delete individual images, and choose which image is primary. The form SHALL reflect the current gallery state and enforce the 6-image cap in the UI.

#### Scenario: Upload multiple images
- **WHEN** an admin uploads several images in the product form
- **THEN** each appears in the form's image manager, the first becoming primary

#### Scenario: Reorder and set primary
- **WHEN** an admin drags images to reorder and marks one as primary
- **THEN** the new order and primary selection are saved via the image-management endpoints

#### Scenario: Delete an image
- **WHEN** an admin removes an image in the form
- **THEN** the image is deleted and, if it was primary, another becomes primary

#### Scenario: Cap enforced in UI
- **WHEN** a product already has 6 images
- **THEN** the upload control is disabled or shows a "maximum reached" message

### Requirement: Product form supports discount fields
The admin product create/edit form SHALL provide inputs for `discount_percent` (integer 1–99, optional), `discount_starts_at`, and `discount_ends_at` (optional datetime pickers). The form SHALL validate client-side that percent is within 1–99, that a start is before an end when both are set, and that a percent is present when any date is set. The form SHALL convert browser-local datetime input to timezone-aware UTC values before submitting, and SHALL convert stored UTC values back to local datetime input values when editing. When a discount is entered the form SHALL preview the resulting sale price. Leaving `discount_percent` empty SHALL submit `discount_percent = null` and clear both datetime fields.

#### Scenario: Set a manual discount
- **WHEN** admin enters `discount_percent` = 20 with no dates and submits
- **THEN** the product is saved with a manual (always-on) discount

#### Scenario: Set a scheduled discount
- **WHEN** admin enters `discount_percent` = 30 with a start and end date and submits
- **THEN** the product is saved with the scheduled window

#### Scenario: Client-side validation blocks invalid window
- **WHEN** admin sets an end date earlier than the start date
- **THEN** an inline validation error is shown and the form is not submitted

#### Scenario: Clearing the discount
- **WHEN** admin blanks the `discount_percent` field on a discounted product and submits
- **THEN** the submitted payload clears `discount_percent`, `discount_starts_at`, and `discount_ends_at`

#### Scenario: Edit scheduled discount displays local time
- **WHEN** admin edits a product whose stored `discount_starts_at` is `2026-08-01 09:30:00` UTC
- **THEN** the datetime picker displays the equivalent local browser time
