# faq-management Specification

## Purpose
TBD - created by archiving change admin-managed-faq. Update Purpose after archive.
## Requirements
### Requirement: FAQ sections storage

The system SHALL persist FAQ sections in a `faq_sections` table keyed by a stable `slug`, with a required `title_en`, optional `title_bg`, an `icon`, `sort_order`, and `created_at`/`updated_at` timestamps. Section slugs SHALL be stable and are used as page anchors; the seeded slugs are `candles`, `care`, `custom`, and `shipping`.

#### Scenario: Sections seeded with stable slugs
- **WHEN** the database is initialized and `faq_sections` is empty
- **THEN** four rows exist with slugs `candles`, `care`, `custom`, `shipping`, each with a non-null `title_en`, an `icon`, and an ascending `sort_order`

#### Scenario: Section slug is immutable
- **WHEN** an admin edits a section
- **THEN** `title_en`, `title_bg`, `icon`, and `sort_order` MAY change but `slug` SHALL NOT change

### Requirement: FAQ items storage

The system SHALL persist FAQ entries in a `faq_items` table with `id`, a `section` referencing `faq_sections(slug)`, required `question_en` and `answer_en`, optional `question_bg` and `answer_bg`, `sort_order`, `is_published` (default 1), and `created_at`/`updated_at` timestamps.

#### Scenario: Item belongs to a section
- **WHEN** an FAQ item is created with `section = "care"`
- **THEN** the row is stored with `section = "care"` and is retrievable ordered by `sort_order` within that section

#### Scenario: English content is required
- **WHEN** an FAQ item is created without `question_en` or without `answer_en`
- **THEN** the system SHALL reject the request with a validation error

### Requirement: Bilingual locale resolution with fallback

The system SHALL resolve localized FAQ text using the requested locale, falling back to English when the Bulgarian value is absent: `en` resolves to the `*_en` value; `bg` resolves to `COALESCE(*_bg, *_en)`. This applies to section titles and to item questions and answers.

#### Scenario: Bulgarian value present
- **WHEN** content is requested with `locale = bg` and `title_bg` is non-null
- **THEN** the system SHALL return `title_bg`

#### Scenario: Bulgarian value missing
- **WHEN** content is requested with `locale = bg` and `answer_bg` is null
- **THEN** the system SHALL return `answer_en`

### Requirement: FAQ content stored raw, escaped at render

FAQ questions and answers are authored by admins (behind `require_admin`) and SHALL be stored as **raw plain text with newlines preserved**. The system SHALL NOT HTML-escape FAQ content on write (unlike anonymous comment/display-name input), so display text is never double-encoded. XSS safety SHALL be provided at render: the frontend relies on React's automatic text escaping, and JSON-LD SHALL be emitted via safe serialization.

#### Scenario: Punctuation preserved verbatim
- **WHEN** an admin saves an answer containing apostrophes, ampersands, or em dashes (e.g. "we'd", "Care & Safety", "home fragrance—more")
- **THEN** the stored value retains those characters unchanged and they render as-is (never as `&#x27;`, `&amp;`, or `&mdash;`)

#### Scenario: Newlines and bullet markers preserved
- **WHEN** an answer contains blank-line-separated paragraphs and lines beginning with `* ` or `- `
- **THEN** those characters are preserved in storage so the renderer can format paragraphs and bullet lists

#### Scenario: Script markup is inert at render
- **WHEN** an answer contains `<script>` or other HTML markup
- **THEN** it is displayed as inert text via React's escaping and is never injected as live HTML, and it is safely serialized inside the JSON-LD block

### Requirement: Seeded initial FAQ content

The system SHALL insert the four sections and all initial FAQ items with the exact approved English copy and a Bulgarian draft via a marker-guarded one-time migration that runs exactly once. Re-running initialization SHALL be a no-op, and edits or deletions of seeded rows SHALL NOT be re-created on later startups.

#### Scenario: Seed populates on first run
- **WHEN** the seed migration runs for the first time
- **THEN** the four sections and all items from the seed content (see Appendix) are inserted with `is_published = 1`

#### Scenario: Seed runs only once
- **WHEN** initialization runs again after the seed migration has already completed
- **THEN** no seed rows are inserted or modified, even if some seeded rows were edited or deleted

### Requirement: Timestamp maintenance

Each table SHALL default `created_at` and `updated_at` to `datetime('now')`, and `updated_at` SHALL be refreshed automatically on row update via an `AFTER UPDATE` trigger (matching the existing `products_updated_at` convention), not by service code.

#### Scenario: updated_at advances on edit
- **WHEN** a row in `faq_items` is updated
- **THEN** its `updated_at` reflects the modification time without the service explicitly setting it

---

