## ADDED Requirements

### Requirement: About page editorial reveal motion
The atelier/about page SHALL reveal eligible editorial sections, card grids, collection cards, and timeline rows as they enter the viewport using the shared scroll-triggered motion primitive.

#### Scenario: Editorial content reveals on scroll
- **WHEN** a user scrolls through the atelier/about page
- **THEN** image/text sections, card-grid items, collection cards, and timeline rows reveal without altering page order or spacing

#### Scenario: Existing links remain usable
- **WHEN** a revealed collection card or CTA contains a link
- **THEN** the link target, focus state, and keyboard accessibility remain unchanged

#### Scenario: About page reduced motion fallback
- **WHEN** reduced motion is enabled
- **THEN** all atelier/about reveal targets render visible without entrance movement or stagger delays
