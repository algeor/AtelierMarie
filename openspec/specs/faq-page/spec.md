# faq-page Specification

## Purpose
TBD - created by archiving change admin-managed-faq. Update Purpose after archive.
## Requirements
### Requirement: Public FAQ page

The system SHALL provide a public FAQ page at `/[locale]/faq` rendered as a server component that fetches content from `GET /v1/faq` for the active locale. The page SHALL present a single centred content column (max width ~850–950px) with a hero (title, subtitle, and a "Contact Us" text link to `/[locale]/contact`), the FAQ sections, a contact banner, and three trust cards.

#### Scenario: Page renders localized content
- **WHEN** a visitor opens `/bg/faq`
- **THEN** the page renders sections and items with Bulgarian text (falling back to English where Bulgarian is absent)

#### Scenario: Hero CTA links to contact
- **WHEN** a visitor clicks the hero "Contact Us" link
- **THEN** they navigate to `/[locale]/contact`

### Requirement: Section presentation and anchors

Each FAQ section SHALL render its icon and localized title with a small decorative accent line beneath it, and the section wrapper SHALL carry `id` equal to the section slug (`candles`, `care`, `custom`, `shipping`) with scroll offset so anchor navigation lands cleanly.

#### Scenario: Anchor scrolls to section
- **WHEN** a visitor navigates to `/[locale]/faq#care`
- **THEN** the page scrolls to the "Candle Care & Safety" section with its heading visible below any fixed header

### Requirement: Accordion behavior

Each question SHALL render as an accordion showing the question with a toggle affordance; opening reveals the answer with a smooth 250–350ms animation. At most one accordion SHALL be open at a time **within a section** — opening a question in one section SHALL NOT close an open question in a different section.

#### Scenario: One open per section
- **WHEN** a visitor opens a second question in the same section
- **THEN** the previously open question in that section closes

#### Scenario: Sections are independent
- **WHEN** a visitor has a question open in the "About" section and opens a question in the "Shipping" section
- **THEN** the "About" question remains open

#### Scenario: Bulleted answer renders as a list
- **WHEN** an answer contains lines beginning with `* ` or `- `
- **THEN** those lines render as a bulleted list and other text renders as paragraphs

### Requirement: Accordion accessibility

Each accordion toggle SHALL be a semantic control (a `<button>`) exposing `aria-expanded` and `aria-controls` referencing its answer panel, operable by keyboard (Enter/Space toggle, visible focus ring). The open/close animation SHALL respect `prefers-reduced-motion`.

#### Scenario: Keyboard operation
- **WHEN** a keyboard user focuses a question and presses Enter or Space
- **THEN** the accordion toggles open/closed and `aria-expanded` updates accordingly

#### Scenario: Reduced motion honored
- **WHEN** the user has `prefers-reduced-motion: reduce` set
- **THEN** the open/close transition is reduced or disabled

### Requirement: Contact banner and trust cards

After the last section the page SHALL render a full-width rounded contact banner ("Still have a question?") with a "Contact Us" button linking to `/[locale]/contact`, followed by three trust cards (Handcrafted, Gift Ready, Customisable). Banner and trust-card text are chrome and SHALL come from `messages/*.json`.

#### Scenario: Banner button links to contact
- **WHEN** a visitor clicks the banner "Contact Us" button
- **THEN** they navigate to `/[locale]/contact`

### Requirement: FAQ structured data and metadata

The page SHALL emit `FAQPage` JSON-LD structured data built from the visible questions and answers, and SHALL set localized page metadata (title, description) via the existing SEO utilities. The JSON-LD SHALL be produced with safe serialization (JSON encoding with `<` escaped) so answer content cannot break out of the `<script>` element.

#### Scenario: JSON-LD present
- **WHEN** the FAQ page is rendered
- **THEN** a `FAQPage` JSON-LD script is included whose questions and answers match the published, localized content

#### Scenario: JSON-LD is injection-safe
- **WHEN** an answer contains characters like `<`, `>`, or the sequence `</script>`
- **THEN** the serialized JSON-LD escapes them so the surrounding `<script>` element is not terminated early

### Requirement: Mobile-friendly presentation

The page SHALL be comfortably browsable on mobile: accordion tap targets SHALL be at least 48px tall, cards SHALL be full width, and horizontal padding SHALL reduce to ~20px on small screens.

#### Scenario: Tap targets meet minimum size
- **WHEN** the page is viewed on a mobile viewport
- **THEN** each accordion question control has a tappable height of at least 48px

