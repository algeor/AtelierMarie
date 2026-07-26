## ADDED Requirements

### Requirement: FAQ admin management page

The system SHALL provide an admin management page at `/[locale]/admin/faq`, protected by the existing admin guard, that lists FAQ items grouped by section and allows creating, editing, deleting, reordering, and publishing/hiding items, and editing section titles.

#### Scenario: Admin views items by section
- **WHEN** an admin opens `/[locale]/admin/faq`
- **THEN** items are listed grouped under their sections, including unpublished items with a clear published/hidden indicator

#### Scenario: Non-admin cannot access
- **WHEN** a non-admin attempts to open the FAQ admin page
- **THEN** access is denied by the admin guard

### Requirement: Side-by-side bilingual editing

The item editor SHALL present English and Bulgarian fields side by side for both question and answer, with English required and Bulgarian optional. Saving SHALL call the admin API and reflect the update in the list.

#### Scenario: Edit both languages in one form
- **WHEN** an admin edits an item and fills both the English and Bulgarian answer fields, then saves
- **THEN** both `answer_en` and `answer_bg` are persisted via the admin API

#### Scenario: English required in form
- **WHEN** an admin tries to save an item with an empty English question or answer
- **THEN** the form SHALL show a validation error and not submit

### Requirement: Manage ordering and visibility

The admin page SHALL allow reordering items within a section and toggling each item's published state, reflecting changes without a full page reload.

#### Scenario: Toggle visibility
- **WHEN** an admin hides an item from the admin page
- **THEN** the item shows as hidden and is removed from the public FAQ page

#### Scenario: Reorder within section
- **WHEN** an admin changes the order of items within a section and saves
- **THEN** the new order is persisted and reflected on the public page
