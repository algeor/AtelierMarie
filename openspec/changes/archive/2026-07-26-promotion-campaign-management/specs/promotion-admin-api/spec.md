## ADDED Requirements

### Requirement: Promotion campaign admin API
The system SHALL expose admin-only promotion campaign endpoints under `/v1/admin/promotions/campaigns`. A campaign SHALL have an ID, name, optional internal note, discount payload (`discount_percent`, `discount_starts_at`, `discount_ends_at`), target definition (explicit product IDs or admin product-list filter descriptor), applied status metadata, timestamps, and derived status (`draft`, `scheduled`, `active`, `ended`, or `removed`). Campaigns are management records only; cart, checkout, and public product pricing SHALL NOT read campaign rows.

Campaign create and update requests SHALL validate discount fields using the same rules as single-product discounts. A campaign target definition SHALL specify exactly one target source. Campaign list and detail responses SHALL include target count and the latest apply/remove result summary when available.

#### Scenario: Create draft campaign with explicit products
- **WHEN** an admin creates a campaign named `Spring Sale` with `discount_percent = 20` and explicit product IDs
- **THEN** the campaign is stored as a management record
- **AND** no product discount fields are changed until the campaign is applied

#### Scenario: Create scheduled campaign
- **WHEN** an admin creates a campaign with a future `discount_starts_at` and valid `discount_ends_at`
- **THEN** the campaign is saved and its derived status is `scheduled`

#### Scenario: Reject invalid campaign discount
- **WHEN** an admin creates a campaign with `discount_percent = 0` or an inverted window
- **THEN** the request is rejected with a validation error

#### Scenario: List campaigns
- **WHEN** an admin requests the campaign list
- **THEN** campaigns are returned with name, derived status, discount summary, target count, and timestamps

### Requirement: Apply campaign to products
The system SHALL expose an admin action to apply a campaign's discount to its target products. Applying a campaign SHALL resolve the campaign's target definition at apply time, enforce the 500-product cap, then update target product discount fields using the same bulk product discount logic as `PATCH /v1/admin/products/bulk-discount`. The campaign SHALL record the resolved product IDs and last applied discount values for later conservative removal.

The apply response SHALL include `success_count`, `failure_count`, and per-product results. Applying a campaign SHALL NOT create a separate runtime pricing rule; the product discount fields remain the runtime source of truth.

#### Scenario: Apply campaign to explicit targets
- **WHEN** an admin applies a campaign targeting products `a` and `b`
- **THEN** products `a` and `b` receive the campaign discount fields
- **AND** the campaign records those product IDs as applied targets

#### Scenario: Apply filter-targeted campaign
- **WHEN** an admin applies a campaign targeting all active products in category `spring`
- **THEN** the server resolves all matching products at apply time and updates those products up to the 500-product cap

#### Scenario: Apply campaign with partial product failure
- **WHEN** one target product cannot be updated
- **THEN** other successful targets remain updated
- **AND** the response includes a failed result for that product

### Requirement: Remove campaign discount conservatively
The system SHALL expose an admin action to remove a campaign's discount from its previously applied products. Removal SHALL clear `discount_percent`, `discount_starts_at`, and `discount_ends_at` only for products whose current discount fields still match the campaign's last applied discount values. Products whose discount fields no longer match SHALL be skipped and reported in the per-product results to avoid clearing newer manual or campaign edits.

#### Scenario: Remove campaign from unchanged products
- **WHEN** an admin removes a campaign whose target products still have the campaign discount fields
- **THEN** those products have all discount fields cleared
- **AND** the response reports them as updated

#### Scenario: Skip product edited after campaign apply
- **WHEN** a target product's discount percent or window differs from the campaign's last applied values
- **THEN** campaign removal does not clear that product's discount
- **AND** the result for that product has `status = skipped` with an explanatory message

### Requirement: Promotion banner admin API
The system SHALL expose admin-only banner settings endpoints under `/v1/admin/promotions/banner`. Admins SHALL be able to read and update the managed banner's localized message, optional link label and URL, enabled flag, and optional active window. Updating visible banner content or schedule SHALL change the public dismiss key so previously dismissed old banner content does not suppress the new banner.

#### Scenario: Update banner message
- **WHEN** an admin updates `message_en` and enables the banner
- **THEN** the public banner endpoint can return the new message while the banner is active

#### Scenario: Update banner schedule changes dismiss key
- **WHEN** an admin changes banner message or active window
- **THEN** the banner dismiss key changes

#### Scenario: Disable banner
- **WHEN** an admin sets `is_enabled = false`
- **THEN** the public banner endpoint returns no active banner
