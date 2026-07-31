# about-public-api Specification

## Purpose
TBD - created by archiving change atelier-story-page. Update Purpose after archive.
## Requirements
### Requirement: Public about endpoint
The system SHALL expose `GET /v1/about?locale=` (no auth) returning published sections in `sort_order`, each with its published items in `sort_order`, localized to a single string per field for the requested locale (default `en`).

#### Scenario: Published, ordered, localized response
- **WHEN** a client requests `GET /v1/about?locale=bg`
- **THEN** the response contains only `is_published = 1` sections and items, ordered by `sort_order`, with each text field resolved to Bulgarian (falling back to English where `*_bg` is NULL)

#### Scenario: Hidden section excluded
- **WHEN** a section has `is_published = 0`
- **THEN** it and its items are absent from the public response

#### Scenario: Response shape carries type and CTA
- **WHEN** the response is returned
- **THEN** each section includes `slug`, `type`, `heading`, optional `subheading`/`body`/`image`, an optional `cta` (`label` + `href`), and an `items` array of `{ id, title, text, image, link }`

#### Scenario: Performance budget
- **WHEN** the endpoint is queried
- **THEN** it responds in under 200ms using indexed queries and does not access Layer 2

