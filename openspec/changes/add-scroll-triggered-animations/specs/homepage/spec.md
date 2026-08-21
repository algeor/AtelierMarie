## ADDED Requirements

### Requirement: Homepage scroll reveal motion
The homepage SHALL reveal eligible sections and repeated card-like items as they enter the viewport using the shared scroll-triggered motion primitive.

#### Scenario: Homepage section headers reveal
- **WHEN** a user scrolls through the homepage
- **THEN** section headers reveal with a fade and small upward slide as they enter the viewport

#### Scenario: Homepage cards reveal in order
- **WHEN** homepage card, category, collection, or timeline items enter the viewport
- **THEN** the items reveal in a subtle staggered order without changing the grid or timeline layout

#### Scenario: Featured products preserve carousel behavior
- **WHEN** featured product cards reveal in the homepage carousel
- **THEN** carousel navigation, swipe behavior, product links, add-to-cart controls, and impression tracking continue to work as before

#### Scenario: Homepage reduced motion fallback
- **WHEN** reduced motion is enabled
- **THEN** all homepage reveal targets render visible without entrance movement or stagger delays
