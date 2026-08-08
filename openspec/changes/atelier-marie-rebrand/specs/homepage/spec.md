## MODIFIED Requirements

### Requirement: Homepage hero section
The system SHALL render a full-width, image-led hero section at the top of the homepage with the Atelier Marie brand name/logo area, a short romantic supporting line, and a primary call-to-action linking to the products page. The hero SHALL use a soft product or atelier lifestyle visual, preferably a woman's hand lighting a candle with free composition space for the brand text. The first viewport SHALL make the brand/product signal clear and SHALL NOT render as a generic marketing block, card-heavy splash, or decorative-only hero.

#### Scenario: Hero section renders with rebrand content
- **WHEN** the homepage loads
- **THEN** a full-width hero section displays with Atelier Marie brand text, a short supporting line, and a primary CTA linking to `/products`
- **AND** the visual treatment uses the rebrand palette and typography instead of the old gradient-only hero direction

#### Scenario: Hero CTA navigates to products
- **WHEN** a user clicks the primary hero CTA
- **THEN** they are navigated to the `/products` page

#### Scenario: Hero media preserves readability
- **WHEN** the hero renders on mobile or desktop
- **THEN** the brand name/logo, supporting copy, and CTA remain readable over the intended free space

#### Scenario: Hero is product-led
- **WHEN** the homepage first viewport renders
- **THEN** product or atelier lifestyle media is the primary visual signal
- **AND** the hero avoids dense cards, excess badges, and clutter that hides the main shopping CTA

## ADDED Requirements

### Requirement: Homepage trust recap
The homepage SHALL include a short trust recap that summarizes the Atelier/About story without duplicating the full about page. It SHALL mention handmade production, premium organic wax blend, high-quality fragrance selection, careful finish, and personal atelier support using calm, supportable wording.

#### Scenario: Trust recap appears on homepage
- **WHEN** the homepage loads
- **THEN** it includes a concise trust recap section with handmade, wax, fragrance, quality, and support signals

#### Scenario: Trust copy avoids unsupported claims
- **WHEN** trust recap copy is authored
- **THEN** organic, premium, and highest-quality claims are phrased only in ways that can be supported by product/supplier information

### Requirement: Homepage mobile-first editorial sequence
The homepage SHALL behave as a vertical mobile-first landing sequence. The sequence SHALL move naturally from hero media to story/trust copy, featured product or product entry, product categories, and footer without scroll traps or hover-only steps.

#### Scenario: Mobile scroll remains natural
- **WHEN** a visitor scrolls the homepage on a mobile viewport
- **THEN** each major landing step appears through normal vertical scrolling
- **AND** pinned or parallax effects do not trap the user or block content access

#### Scenario: Featured product becomes shoppable in the flow
- **WHEN** featured products are available in the landing sequence
- **THEN** product title, price, detail navigation, and shopping actions remain visible and usable as the product enters the flow

#### Scenario: Story text appears without disconnecting the product visual
- **WHEN** the landing story/trust copy appears during the sequence
- **THEN** the copy remains visually connected to product or atelier media rather than feeling like an unrelated text block

### Requirement: Homepage product category entry points
The homepage SHALL display product category entry points near the top of the landing flow. Categories SHALL render only when at least one product exists for that category/type. Initial category artwork SHALL support Christmas balls, custom boxes, candles, and notebooks. On mobile, categories SHALL render as a horizontally scrollable row or compact grid with stable tile dimensions.

#### Scenario: Empty categories are hidden
- **WHEN** no active product exists for a category/type
- **THEN** that category is not shown on the homepage

#### Scenario: Available categories render with line drawings
- **WHEN** active products exist for Christmas balls, custom boxes, candles, or notebooks
- **THEN** the corresponding category entry renders with a delicate one-line drawing and a short readable label

#### Scenario: Category click opens filtered products
- **WHEN** a visitor activates a homepage category entry
- **THEN** they are navigated to the products page with that category/type selected or encoded in the URL

#### Scenario: Category layout is stable on mobile
- **WHEN** animated category drawings render on a mobile viewport
- **THEN** category tile dimensions remain stable before, during, and after animation

#### Scenario: Category transition supports navigation
- **WHEN** a category activation uses an editorial transition
- **THEN** the transition does not delay the route change, break browser navigation, or prevent keyboard activation

### Requirement: Homepage hero media asset handling
The homepage hero SHALL use optimized local media assets suitable for web delivery. Source media MAY come from `/Users/I551270/Desktop/untitled folder`, but selected assets SHALL be copied/processed into the frontend public/static asset area before use. If a moving flame/cinemagraph effect is used, the page SHALL provide a still-image fallback and SHALL respect reduced-motion preferences.

#### Scenario: Hero media uses optimized app asset
- **WHEN** the homepage hero renders
- **THEN** image/video sources are served from the app's public/static asset paths rather than a local desktop source folder

#### Scenario: Moving flame has still fallback
- **WHEN** moving flame hero media is unavailable, fails to load, or reduced motion is enabled
- **THEN** the homepage renders a still image or static visual fallback without breaking the hero layout

#### Scenario: Hero media does not obscure product
- **WHEN** the hero media renders
- **THEN** the candle/product remains visible and is not hidden by heavy blur, dark overlays, or cropped text/logo placement

### Requirement: Homepage luxury motion behavior
Homepage motion SHALL feel slow, soft, and editorial. Allowed motion includes hero reveal, gentle media movement, line drawing, trust item reveal, product image settling, and footer wordmark reveal. Motion SHALL use transform/opacity where possible and SHALL respect reduced-motion preferences. Homepage motion SHALL NOT use jittery, bouncy, spinning, shaking, confetti, or loud hover effects.

#### Scenario: Reduced motion disables decorative homepage motion
- **WHEN** the user has `prefers-reduced-motion: reduce` enabled
- **THEN** decorative homepage animations are disabled or reduced while all content remains visible and usable

#### Scenario: Homepage motion does not delay shopping actions
- **WHEN** a visitor clicks a CTA, category, product card, or add-to-cart action
- **THEN** the action remains immediate and is not blocked by decorative animation

#### Scenario: Homepage motion remains restrained
- **WHEN** decorative homepage motion is active
- **THEN** it guides attention without resizing fixed-format UI, overlapping text, or obscuring shopping controls

### Requirement: Existing homepage commerce functionality is preserved
The homepage SHALL preserve existing exposed commerce functionality, including featured product loading, featured product cards, product detail links, localized copy, loading states, and empty-featured behavior.

#### Scenario: Featured products still render
- **WHEN** featured products exist
- **THEN** the homepage displays them with product image/placeholder, product name, price, and link to product detail

#### Scenario: No featured products remains safe
- **WHEN** no products have `is_featured` set to true
- **THEN** the homepage does not render an empty broken featured-products grid
