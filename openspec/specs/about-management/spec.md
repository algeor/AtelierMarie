# about-management Specification

## Purpose
TBD - created by archiving change atelier-story-page. Update Purpose after archive.
## Requirements
### Requirement: About content model
The system SHALL store atelier-story content in two SQLite tables: `about_sections` (seeded, fixed `slug` primary key and fixed render `type`) and `about_items` (child rows referencing a section slug). All content is Layer 1 (SQLite, WAL) and MUST NOT touch Layer 2.

#### Scenario: Tables created on startup
- **WHEN** the application starts
- **THEN** `about_sections` and `about_items` are created if absent, with an index on `about_items(section, sort_order)`

#### Scenario: Section slug and type are stable
- **WHEN** an admin edits a section
- **THEN** its `slug` and `type` cannot be changed, and no new section or section type can be created via the API

### Requirement: Bilingual storage with locale fallback
Every user-facing text field SHALL be stored as an `_en` (required) and `_bg` (nullable) pair. Localized resolution SHALL return `*_en` for locale `en` and `COALESCE(*_bg, *_en)` for locale `bg`.

#### Scenario: Bulgarian falls back to English
- **WHEN** a field's `*_bg` value is NULL and the requested locale is `bg`
- **THEN** the English value is returned instead of an empty string

### Requirement: Text sanitization on write
All section and item text SHALL pass through `app/utils/sanitize.py` before persistence to strip HTML/scripts.

#### Scenario: HTML stripped from body
- **WHEN** an admin submits body text containing `<script>` or other HTML
- **THEN** the stored value has the HTML/script content removed

### Requirement: Admin-uploaded images via existing pipeline
Section and item image fields SHALL store a WebP `image_id` produced by `app/services/image_service.py` (magic-byte validation, resize, EXIF strip, path-traversal prevention). No new storage subsystem is introduced.

#### Scenario: Non-image upload rejected
- **WHEN** an admin uploads a file whose magic bytes are not a supported image type
- **THEN** the upload is rejected and no `image_id` is stored

### Requirement: Idempotent bilingual seed
On startup, if `about_sections` is empty, the system SHALL seed all ten sections and their items with the exact English copy and drafted Bulgarian from `seed-content.md`, all `is_published = 1`. Seeding SHALL NOT overwrite existing rows.

#### Scenario: Seed runs once
- **WHEN** the app starts and `about_sections` already contains rows
- **THEN** no seed rows are inserted or overwritten

