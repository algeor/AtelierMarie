## ADDED Requirements

### Requirement: Public FAQ endpoint

The system SHALL expose `GET /v1/faq` returning published FAQ content grouped by section, localized to the requested locale. The endpoint SHALL require no authentication and SHALL respond in under 200ms.

#### Scenario: Returns sections with published items
- **WHEN** a client requests `GET /v1/faq?locale=en`
- **THEN** the response contains sections ordered by section `sort_order`, each with `slug`, localized `title`, `icon`, and its published `items` ordered by item `sort_order`

#### Scenario: Items shaped as localized question/answer
- **WHEN** the endpoint returns an item
- **THEN** each item has `id`, a single localized `question` string, and a single localized `answer` string (no `*_en`/`*_bg` fields exposed)

### Requirement: Localized public response with fallback

The public endpoint SHALL localize every field using the requested locale with English fallback: `locale=en` returns `*_en`; `locale=bg` returns `COALESCE(*_bg, *_en)`. An absent or unsupported `locale` SHALL default to `en`.

#### Scenario: Bulgarian request falls back per field
- **WHEN** a client requests `GET /v1/faq?locale=bg` and a given item has `answer_bg` null but `question_bg` set
- **THEN** that item's `answer` is the English text and its `question` is the Bulgarian text

#### Scenario: Unknown locale defaults to English
- **WHEN** a client requests `GET /v1/faq?locale=fr`
- **THEN** the response is localized to English

### Requirement: Published-only visibility with stable section anchors

The public endpoint SHALL return only items with `is_published = 1`. Hidden items SHALL be excluded. The four seeded sections SHALL always be present in the response (even with an empty `items` list) so their anchors (`#candles`, `#care`, `#custom`, `#shipping`) — which product pages deep-link to — never dead-end.

#### Scenario: Hidden item excluded
- **WHEN** an item has `is_published = 0`
- **THEN** it does not appear in the `GET /v1/faq` response

#### Scenario: Seeded section with no published items still returned
- **WHEN** every item in a seeded section is unpublished or deleted
- **THEN** that section is still returned with an empty `items` list, preserving its anchor slug
