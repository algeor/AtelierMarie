## ADDED Requirements

### Requirement: Admin FAQ item listing

The system SHALL expose admin FAQ endpoints under `/v1/admin/faq` protected by the `require_admin` dependency. The admin listing SHALL return items grouped by section with both languages and publication state exposed (`question_en`, `question_bg`, `answer_en`, `answer_bg`, `sort_order`, `is_published`).

#### Scenario: Admin sees both languages
- **WHEN** an admin requests the FAQ item list
- **THEN** each item includes its `*_en` and `*_bg` values and `is_published`, including unpublished items

#### Scenario: Non-admin rejected
- **WHEN** a request without valid admin credentials hits any `/v1/admin/faq` endpoint
- **THEN** the system SHALL respond 401/403 and perform no change

### Requirement: Create, update, and delete FAQ items

The system SHALL allow admins to create, update, and delete FAQ items. Create requires `section`, `question_en`, and `answer_en`; `*_bg` values are optional. Text SHALL be sanitized on write. Deleting an item SHALL remove it permanently.

#### Scenario: Create item
- **WHEN** an admin POSTs a new item with a valid `section`, `question_en`, and `answer_en`
- **THEN** the item is stored with `is_published = 1` by default and appears in the admin listing

#### Scenario: Update Bulgarian translation
- **WHEN** an admin PATCHes an item to set `answer_bg`
- **THEN** the stored `answer_bg` is updated and `updated_at` is refreshed

#### Scenario: Create with unknown section rejected
- **WHEN** an admin creates an item with a `section` that is not a seeded section slug
- **THEN** the system SHALL reject the request with a validation error

#### Scenario: Delete item
- **WHEN** an admin deletes an item
- **THEN** the item is removed and no longer returned by public or admin endpoints

### Requirement: Publish/hide toggle

The system SHALL allow admins to toggle an item's `is_published` state without deleting it.

#### Scenario: Hide an item
- **WHEN** an admin sets `is_published = 0` on an item
- **THEN** the item remains in the admin listing but is excluded from `GET /v1/faq`

### Requirement: Reorder items within a section

The system SHALL allow admins to reorder items within a section by updating `sort_order`. Ordering is scoped per section.

#### Scenario: Reorder persists
- **WHEN** an admin submits a new ordering for items in section `care`
- **THEN** subsequent public and admin responses return those items in the new order

### Requirement: Edit section titles

The system SHALL allow admins to edit a section's `title_en`, `title_bg`, `icon`, and `sort_order`. The section `slug` SHALL NOT be editable.

#### Scenario: Update section title
- **WHEN** an admin PATCHes section `custom` with a new `title_bg`
- **THEN** the stored `title_bg` updates and the `slug` remains `custom`

#### Scenario: Slug change rejected
- **WHEN** an admin attempts to change a section's `slug`
- **THEN** the system SHALL reject or ignore the slug change and preserve the original slug
