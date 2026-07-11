## ADDED Requirements

### Requirement: Admin product form supports dual-language input
The system SHALL provide input fields for both English and Bulgarian content when creating or editing products. Both `name_en`/`name_bg` and `description_en`/`description_bg` fields SHALL be visible in the admin product form.

#### Scenario: Creating a product with both languages
- **WHEN** an admin creates a product and fills in both EN and BG name/description fields
- **THEN** the product is saved with content in both languages

#### Scenario: Creating a product with one language only
- **WHEN** an admin creates a product and fills in only the EN fields (BG fields left empty)
- **THEN** the product is saved with EN content; BG fields remain NULL (fallback applies on display)

### Requirement: Staleness indicator in admin UI
The system SHALL display a visual indicator (warning badge) next to product content fields that are flagged as stale (out of sync with the other language).

#### Scenario: Stale Bulgarian content shows warning
- **WHEN** an admin views a product where `translation_stale_bg = true`
- **THEN** the BG content fields display a visual staleness indicator (e.g., ⚠️ badge)

#### Scenario: Updated content clears warning
- **WHEN** an admin updates the stale BG content and saves
- **THEN** the staleness indicator disappears

### Requirement: Admin UI itself is bilingual
The admin panel UI (navigation, labels, buttons, form labels) SHALL render in the active locale, following the same locale detection and toggle as the public-facing site.

#### Scenario: Admin panel in Bulgarian
- **WHEN** an admin accesses the admin panel under `/bg/admin/...`
- **THEN** all admin UI labels, navigation, and buttons render in Bulgarian

#### Scenario: Admin panel in English
- **WHEN** an admin accesses the admin panel under `/en/admin/...`
- **THEN** all admin UI labels, navigation, and buttons render in English
