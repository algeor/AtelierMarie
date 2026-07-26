## ADDED Requirements

### Requirement: Public atelier page
The system SHALL serve a public page at `/[locale]/atelier` (server component) that fetches `GET /v1/about`, renders each section by its `type`, and sets page metadata. The page SHALL be responsive and stack image/title/text/button vertically on mobile.

#### Scenario: Sections render in order by type
- **WHEN** a visitor opens `/en/atelier`
- **THEN** each returned section is rendered by the component matching its `type`, in `sort_order`

#### Scenario: Unknown type is skipped
- **WHEN** a section has a `type` with no matching renderer
- **THEN** it is skipped without breaking the page

### Requirement: Section renderers by type
The page SHALL provide a distinct renderer for each type: `hero`, `text_image`, `text_band`, `cards`, `timeline`, `collections`, `cta_band`. Body text SHALL render blank-line blocks as paragraphs and consecutive `* `/`- ` lines as a bulleted list.

#### Scenario: Cards section renders its items as a grid
- **WHEN** a `cards` section is rendered
- **THEN** its published items appear as a grid of cards (title + text) with subtle shadow and rounded corners

#### Scenario: Missing image shows placeholder
- **WHEN** a section or item with an image slot has no `image`
- **THEN** a tasteful placeholder is shown instead of a broken image

### Requirement: Stable section anchors
Each section wrapper SHALL have `id={slug}` and `scroll-margin-top` so deep links (e.g. `/atelier#process`) scroll to the section regardless of section order.

#### Scenario: Deep link after reorder
- **WHEN** sections have been reordered and a visitor opens `/atelier#process`
- **THEN** the page scrolls to the `process` section by its slug anchor

### Requirement: Structured data
The page SHALL emit JSON-LD (`AboutPage`/`Organization`) via `lib/seo.ts`.

#### Scenario: JSON-LD present
- **WHEN** the page is rendered
- **THEN** a valid JSON-LD script describing the brand/about page is included in the document
