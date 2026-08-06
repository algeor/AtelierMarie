## MODIFIED Requirements

### Requirement: Accordion behavior
Each question SHALL render as a collapsed-by-default accordion showing the question with a clear toggle affordance. Opening reveals the answer with a smooth 250-350ms animation. At most one accordion SHALL be open at a time within a section unless a later design decision explicitly allows multiple; opening a question in one section SHALL NOT close an open question in a different section.

#### Scenario: Questions collapsed by default
- **WHEN** a visitor opens the FAQ page
- **THEN** all FAQ questions are collapsed by default

#### Scenario: One open per section
- **WHEN** a visitor opens a second question in the same section
- **THEN** the previously open question in that section closes

#### Scenario: Sections are independent
- **WHEN** a visitor has a question open in the `About` section and opens a question in the `Shipping` section
- **THEN** the `About` question remains open

#### Scenario: Question can be collapsed again
- **WHEN** a visitor activates an already-open question
- **THEN** that question collapses and its answer is hidden

#### Scenario: Bulleted answer renders as a list
- **WHEN** an answer contains lines beginning with `* ` or `- `
- **THEN** those lines render as a bulleted list and other text renders as paragraphs

## ADDED Requirements

### Requirement: Horizontal FAQ category navigation
The FAQ page SHALL present FAQ categories/sections as a horizontally scrollable category strip. The active category SHALL be visually clear and keyboard accessible. Switching category SHALL show the relevant collapsed questions without losing accessible section anchors.

#### Scenario: Categories scroll horizontally on mobile
- **WHEN** the FAQ page is viewed on a mobile viewport with multiple categories
- **THEN** the category controls are available in a horizontal scroll area with comfortable tap targets

#### Scenario: Active category is clear
- **WHEN** a visitor selects a category
- **THEN** the selected category has a visible active state and the visible questions correspond to that category

#### Scenario: Category controls are keyboard accessible
- **WHEN** a keyboard user navigates the category controls
- **THEN** each category can be focused and activated without requiring pointer interaction

### Requirement: FAQ popup-like panels remain in-page
FAQ answers SHALL feel like soft popup-like panels or paper reveals, but SHALL remain in the page flow rather than using blocking modal dialogs.

#### Scenario: Answer opens without modal trap
- **WHEN** a visitor expands a FAQ question
- **THEN** the answer appears inline on the page
- **AND** keyboard focus is not trapped in a modal overlay

### Requirement: FAQ questions reveal one by one
FAQ question controls MAY appear with a soft one-by-one reveal when a visitor opens the FAQ page or switches categories. The reveal SHALL keep every answer collapsed by default, SHALL use in-page controls rather than modal dialogs, and SHALL provide a reduced-motion fallback that shows the same questions without staggered decorative motion.

#### Scenario: Questions enter collapsed during reveal
- **WHEN** FAQ questions appear one by one after page load or category change
- **THEN** each question control appears collapsed
- **AND** no answer opens automatically

#### Scenario: Reduced motion removes stagger
- **WHEN** the user has `prefers-reduced-motion: reduce` enabled
- **THEN** FAQ questions render without staggered popup-like motion while remaining readable and interactive
