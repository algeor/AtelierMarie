# about-admin-ui Specification

## Purpose
TBD - created by archiving change atelier-story-page. Update Purpose after archive.
## Requirements
### Requirement: Admin atelier management UI
The system SHALL provide an admin page at `/[locale]/admin/atelier` that lists sections in order and allows editing all content, gated by the existing admin guard.

#### Scenario: Sections listed in order
- **WHEN** an admin opens `/en/admin/atelier`
- **THEN** all sections (including hidden ones) are shown in `sort_order` with their type and publish state

### Requirement: Side-by-side bilingual editing
Each edit form SHALL present English and Bulgarian fields side by side for headings, subheadings, body, CTA labels, and item title/text.

#### Scenario: Edit both languages in one form
- **WHEN** an admin edits a section
- **THEN** the form shows `*_en` and `*_bg` inputs together and saves both in one request

### Requirement: Image upload, item management, reorder, and toggle in UI
The UI SHALL support uploading/clearing a section or item image, creating/editing/deleting items, reordering sections and items, and toggling publish state.

#### Scenario: Upload a hero image
- **WHEN** an admin selects an image for the hero section and saves
- **THEN** the image is uploaded via the admin API and the section preview shows the new image

#### Scenario: Toggle section visibility
- **WHEN** an admin toggles a section's publish switch off
- **THEN** the section is marked hidden and will not appear on the public page

