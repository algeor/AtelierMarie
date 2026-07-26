## ADDED Requirements

### Requirement: FAQ links on product detail

The product detail page SHALL surface contextual links to the relevant FAQ sections — "Candle Care" (`/[locale]/faq#care`), "Custom Orders" (`/[locale]/faq#custom`), and "Shipping & Returns" (`/[locale]/faq#shipping`) — so customers can find answers where they naturally look.

#### Scenario: Contextual FAQ links present
- **WHEN** a visitor views a product detail page
- **THEN** links to the Candle Care, Custom Orders, and Shipping & Returns FAQ sections are shown, each navigating to the matching FAQ section anchor

### Requirement: Questions link near Add to Cart

The product detail page SHALL include a small "Questions?" link near the Add to Cart button that navigates to the relevant FAQ section anchor.

#### Scenario: Questions link jumps to FAQ
- **WHEN** a visitor clicks the "Questions?" link near Add to Cart
- **THEN** they navigate to the FAQ page at the relevant section anchor (e.g. `/[locale]/faq#care`)
