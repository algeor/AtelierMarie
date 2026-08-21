## ADDED Requirements

### Requirement: Product listing card reveal motion
Product listing pages SHALL reveal product cards as they enter the viewport using the shared scroll-triggered motion primitive.

#### Scenario: Product cards reveal on scroll
- **WHEN** a user scrolls through a product grid
- **THEN** product cards fade and slide into their final position as they become visible

#### Scenario: Product card interactions remain unchanged
- **WHEN** a revealed product card is clicked, saved, or added to cart
- **THEN** the existing product navigation, save action, add-to-cart action, and analytics tracking continue to work

#### Scenario: Product listing reduced motion fallback
- **WHEN** reduced motion is enabled
- **THEN** product cards render visible without entrance movement or stagger delays
