# about-admin-api Specification

## Purpose
TBD - created by archiving change atelier-story-page. Update Purpose after archive.
## Requirements
### Requirement: Admin about API behind require_admin
The system SHALL expose management endpoints under `/v1/admin/about`, all protected by the `require_admin` dependency (JWT `is_admin` or Bearer API key). Admin reads SHALL return raw bilingual fields (`*_en` and `*_bg`), `is_published`, and `image_id`.

#### Scenario: Unauthenticated request rejected
- **WHEN** a request to any `/v1/admin/about` endpoint lacks admin credentials
- **THEN** the API responds 401/403 and performs no mutation

### Requirement: Edit section text and CTA
The system SHALL allow `PATCH /v1/admin/about/sections/{slug}` to update a section's bilingual heading/subheading/body and CTA label/href. Slug and type are immutable.

#### Scenario: Update Bulgarian heading
- **WHEN** an admin PATCHes a section with a new `heading_bg`
- **THEN** the stored `heading_bg` is updated (sanitized) and `updated_at` is refreshed

#### Scenario: Slug/type change rejected
- **WHEN** an admin attempts to change `slug` or `type`
- **THEN** the request is rejected

### Requirement: Item CRUD
The system SHALL allow creating, updating, and deleting `about_items` within a section via `POST`/`PATCH`/`DELETE` under the section's slug.

#### Scenario: Create item under a cards section
- **WHEN** an admin POSTs a new item with `title_en` (and optional `_bg`/text)
- **THEN** the item is created under that section with the next `sort_order`

### Requirement: Reorder and publish toggle
The system SHALL allow reordering sections (`POST /v1/admin/about/sections/reorder`) and items within a section, and toggling `is_published` on any section or item. Reordering SHALL NOT change slugs.

#### Scenario: Reorder sections
- **WHEN** an admin submits a new ordering of section slugs
- **THEN** each section's `sort_order` is updated to match, and public output reflects the new order

#### Scenario: Hide a section
- **WHEN** an admin sets a section's `is_published` to 0
- **THEN** the section is retained in admin reads but excluded from public output

### Requirement: Section and item image upload/clear
The system SHALL allow uploading an image to a section or item (multipart `POST .../image`) and clearing it (`DELETE .../image`), processing uploads through `image_service` to a WebP `image_id`.

#### Scenario: Clear an image
- **WHEN** an admin DELETEs a section's image
- **THEN** `image_id` is set to NULL and the public response omits the image for that section

