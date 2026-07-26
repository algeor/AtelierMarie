## ADDED Requirements

### Requirement: Retina-crisp gallery hero
The product gallery hero SHALL render the main (`image_url`) derivative, which is sized large enough (max 2000×2500) to appear crisp on high-density (2×) displays at the gallery's on-page layout size without browser upscaling.

#### Scenario: Hero renders the main derivative
- **WHEN** the product detail page renders a product with images
- **THEN** the hero image `src` resolves to the selected image's `image_url` (main) derivative

### Requirement: Click-to-zoom lightbox
The product gallery SHALL provide a click-to-zoom affordance on the hero image that opens an accessible lightbox displaying the high-resolution `zoom_url` derivative. The zoom asset SHALL be loaded lazily — only when the lightbox is opened, not on initial page load.

#### Scenario: Open zoom lightbox
- **WHEN** the customer activates the zoom affordance on the hero image
- **THEN** a lightbox opens rendering the selected image's `zoom_url`, and the zoom asset is requested at that point (not before)

#### Scenario: Lightbox is keyboard accessible
- **WHEN** the lightbox is open
- **THEN** it exposes a dialog role, traps focus, and closes on Escape or backdrop click

#### Scenario: Zoom fallback when no zoom asset
- **WHEN** the selected image has a null or absent `zoom_url`
- **THEN** the lightbox falls back to rendering `image_url` rather than failing
