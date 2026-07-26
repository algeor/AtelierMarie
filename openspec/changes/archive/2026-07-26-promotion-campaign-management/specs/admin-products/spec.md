## ADDED Requirements

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
