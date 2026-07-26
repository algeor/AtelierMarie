## ADDED Requirements

### Requirement: Admin promotions route
The admin UI SHALL provide a Promotions section at `/admin/promotions` and SHALL add a Promotions item to the admin sidebar. The route SHALL be admin-only and SHALL provide access to campaign management and top banner settings without requiring code changes or redeploys.

#### Scenario: Promotions nav item is visible
- **WHEN** an admin views the admin sidebar
- **THEN** a Promotions navigation item links to `/admin/promotions`

#### Scenario: Promotions route is protected
- **WHEN** a non-admin attempts to access `/admin/promotions`
- **THEN** the existing admin auth guard prevents access

#### Scenario: Promotions page shows campaign and banner areas
- **WHEN** an admin opens `/admin/promotions`
- **THEN** the page exposes campaign management and top banner settings, either as tabs or clearly separated sections

### Requirement: Admin campaign management UI
The Promotions page SHALL let admins create, edit, list, apply, and remove promotion campaigns. The campaign form SHALL include campaign name, optional internal note, discount percent, optional start/end datetimes, and target selection. The campaign list SHALL show campaign name, derived status, discount summary, active window, target count, and available actions.

Datetime inputs SHALL follow the same browser-local to UTC conversion behavior as the single-product discount form. Client-side validation SHALL enforce discount percent 1-99, percent required when any date is set, and start before end when both dates are set.

#### Scenario: Create campaign draft
- **WHEN** an admin enters campaign name, discount percent, and targets, then saves
- **THEN** the campaign appears in the campaign list without changing products until Apply is confirmed

#### Scenario: Client-side validation blocks invalid campaign
- **WHEN** an admin enters `discount_percent = 100` or an end date before the start date
- **THEN** inline validation errors are shown and the campaign is not submitted

#### Scenario: Apply campaign confirmation
- **WHEN** an admin clicks Apply on a campaign
- **THEN** the UI shows a confirmation summary with discount percent, window, and target count before submitting

#### Scenario: Campaign apply result summary
- **WHEN** the campaign apply endpoint returns successes and failures
- **THEN** the UI shows success and failure counts and exposes failed product IDs and messages

#### Scenario: Remove campaign confirmation
- **WHEN** an admin clicks Remove Discount on an applied campaign
- **THEN** the UI asks for confirmation and explains that only unchanged campaign-applied product discounts will be cleared

### Requirement: Campaign target selection UI
The campaign form SHALL support explicit product selection and all-matching-filter selection. Explicit selection SHALL allow admins to select products across pages using a client-side selected-ID set. Filter selection SHALL store the current admin product filters as the target descriptor and show the resolved target count when available.

#### Scenario: Select explicit products across pages
- **WHEN** an admin selects products on multiple admin product list pages for a campaign
- **THEN** the campaign target summary includes all selected product IDs

#### Scenario: Select all matching filter for campaign
- **WHEN** an admin chooses all products matching a filter
- **THEN** the campaign stores the filter descriptor and displays the matching count

#### Scenario: Switching target mode clears previous target
- **WHEN** an admin switches from explicit IDs to filter targeting
- **THEN** the previous explicit selection is cleared or ignored so only one target source is submitted

### Requirement: Admin top banner editor
The Promotions page SHALL provide a top banner editor for the managed site announcement banner. The editor SHALL include localized message fields, optional localized link label fields, optional link URL, enabled toggle, optional start/end datetime inputs, and a preview of the banner. Saving the editor SHALL update the admin banner API.

#### Scenario: Edit and enable banner
- **WHEN** an admin enters a banner message and turns the enabled toggle on
- **THEN** the banner settings are saved and can appear on the storefront while active

#### Scenario: Banner editor previews message
- **WHEN** an admin edits banner text or link fields
- **THEN** the editor shows a preview resembling the storefront top banner

#### Scenario: Banner schedule validation
- **WHEN** an admin enters an end date before the start date
- **THEN** the editor shows an inline validation error and does not submit

#### Scenario: Disable banner from admin
- **WHEN** an admin turns the enabled toggle off and saves
- **THEN** the storefront no longer displays the banner
