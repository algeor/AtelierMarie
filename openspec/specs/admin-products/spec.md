## Purpose

Defines admin product management behavior, including product editing, media controls, catalog fields, and admin-facing product workflows.

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

### Requirement: Product list multi-select

The admin products list SHALL let an admin select multiple product rows and SHALL provide a "select all matching current filter" affordance that targets the active filter descriptor rather than only the loaded page. The current selection count SHALL be visible while a selection is active.

#### Scenario: Select individual rows
- **WHEN** an admin toggles the checkbox on one or more product rows
- **THEN** those products form the current selection and the selection count updates

#### Scenario: Select all matching filter
- **WHEN** an admin chooses "select all matching" while a filter is active
- **THEN** the bulk action targets the current filter descriptor rather than an enumerated list of the loaded rows

### Requirement: Inline bulk discount action bar

When a product selection is active, the admin products list SHALL show a bulk action bar to apply or clear a discount on the selection by calling the bulk discount endpoint. Applying SHALL collect a discount percent (1–99) and an optional start/end window; clearing SHALL remove the discount. The action SHALL surface the per-item result as a summary (for example "N updated, M failed") rather than a raw error or silent success. This inline flow reuses the same bulk discount endpoint and validation as the `/admin/promotions` campaign target picker.

#### Scenario: Apply discount to selection from the products list
- **WHEN** an admin has products selected and submits the apply-discount action with a valid percent and optional window
- **THEN** the discount is applied to the selection via the bulk discount endpoint and a summary shows the updated and failed counts

#### Scenario: Clear discount on selection from the products list
- **WHEN** an admin selects the clear-discount action for the current selection
- **THEN** the discount is removed from the selected products and a result summary is shown

#### Scenario: Partial failure surfaced inline
- **WHEN** a bulk apply from the products list returns some failed products
- **THEN** the UI shows a summary such as "N updated, M failed" and does not report the whole action as a plain success or a raw error

### Requirement: Admin can manage a product's video
Admin product management SHALL allow uploading, replacing, and deleting a single product video, and SHALL display its processing status and any failure reason. The upload endpoint SHALL require admin authorization. Uploading a video for a product that already has one SHALL replace the existing video.

#### Scenario: Admin uploads a video
- **WHEN** an authorized admin uploads a valid video for a product
- **THEN** the video is accepted for processing and the admin view shows status `processing`

#### Scenario: Admin sees a failure reason
- **WHEN** a product's video is in status `failed`
- **THEN** the admin product view shows the human-readable `failure_reason`
- **AND** offers a re-upload action

#### Scenario: Admin deletes a video
- **WHEN** an authorized admin deletes a product's video
- **THEN** the video row and its output files are removed and the product has no video

#### Scenario: Non-admin cannot upload
- **WHEN** an unauthenticated or non-admin caller attempts to upload a product video
- **THEN** the request is rejected with `401`/`403`

### Requirement: Admin controls the video's gallery position
Admin SHALL be able to set the video's `sort_order` so it appears at a chosen position among the product's gallery images. The image gallery ordering (`product_images`) is unaffected by this control.

#### Scenario: Admin positions the video in the gallery
- **WHEN** an admin sets the video's `sort_order`
- **THEN** the public product's `video.sort_order` reflects the new position
- **AND** the detail-page gallery renders the video slide at that position among the images

### Requirement: Large image upload soft-warning and hard block
The admin image upload UI SHALL check a selected file's size on the client before uploading and apply a tiered response: files under 15MB upload without prompting; files from 15MB up to and including 25MB trigger a confirmation dialog warning that the image is large before proceeding; files over 25MB are blocked client-side with an inline error and never uploaded. These client checks are UX only — the backend independently enforces the 25MB hard limit.

#### Scenario: Small file uploads silently
- **WHEN** the admin selects an image smaller than 15MB
- **THEN** the upload proceeds without any warning dialog

#### Scenario: Large file triggers confirmation
- **WHEN** the admin selects an image between 15MB and 25MB (inclusive)
- **THEN** a confirmation dialog appears warning the image is large and stating its size, with Cancel and "Add anyway" actions
- **AND** the upload proceeds only if the admin confirms; cancelling aborts the upload

#### Scenario: Oversized file blocked before upload
- **WHEN** the admin selects an image larger than 25MB
- **THEN** an inline error states the 25MB maximum and no upload request is made

### Requirement: Product image crop/rotate/zoom editor
When an admin selects an image file in the product form, the system SHALL present an interactive editor that allows cropping, rotating, and zooming/panning the image, with the crop frame locked to the storefront display aspect ratio of `4/5`. On confirmation, the framed result SHALL be exported (client-side, via canvas) to an image blob, and that blob — not the originally selected file — SHALL enter the upload flow. On cancel, the selected file SHALL be discarded and not uploaded.

The editor SHALL sit in front of the existing image-management rules without weakening them: the 6-image-per-product limit, image ordering, primary-image selection, the 15–25MB soft-warning confirmation, and the >25MB client-side block all continue to apply to the exported blob.

#### Scenario: Editor opens on image selection
- **WHEN** an admin selects a JPEG or PNG file in the product form
- **THEN** a crop/rotate/zoom editor opens with the crop frame locked to a `4/5` aspect ratio

#### Scenario: Confirmed edit uploads the framed image
- **WHEN** the admin adjusts crop/rotation/zoom and confirms
- **THEN** the framed image is exported to a blob and that blob is added to the pending upload set (the original selected file is not uploaded)

#### Scenario: Cancelled edit discards the file
- **WHEN** the admin cancels the editor
- **THEN** no image is added to the pending upload set and no upload occurs

#### Scenario: Framed output matches storefront framing
- **WHEN** the framed blob is uploaded and later displayed on the storefront card
- **THEN** the visible framing matches what the admin saw in the editor (no additional `object-cover` cropping surprises), because both use the `4/5` aspect ratio

#### Scenario: Existing image limits still apply to the exported blob
- **WHEN** adding the exported blob would exceed 6 images, or the blob exceeds 25MB
- **THEN** the existing limit/size rules reject or warn exactly as they do for a directly selected file
