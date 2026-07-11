## ADDED Requirements

### Requirement: Homepage hero section
The system SHALL render a full-width hero section at the top of the homepage (breaking out of the max-w-7xl container) with a headline, subtitle, and call-to-action button linking to the products page.

#### Scenario: Hero section renders with content
- **WHEN** the homepage loads
- **THEN** a full-width hero section (outside the max-width container) displays with a brand-palette gradient background (warm-ivory → dusty-pink), a headline in Playfair Display, a subtitle in Inter, and a primary CTA button ("Shop Collection") linking to /products

#### Scenario: Hero CTA navigates to products
- **WHEN** a user clicks the "Shop Collection" button
- **THEN** they are navigated to the /products page

#### Scenario: Hero uses gradient background (no external image dependency)
- **WHEN** the homepage loads
- **THEN** the hero uses a CSS gradient background (no external image required for Day 3). A hero image can be added later as a static asset in `public/images/`.

### Requirement: Featured products grid on homepage
The system SHALL display a grid of featured products on the homepage, sourced by filtering the product list for `is_featured === true`.

#### Scenario: Featured products display in responsive grid
- **WHEN** the homepage loads and featured products exist
- **THEN** featured products render in a grid: 4 columns on desktop (>1024px), 2 columns on tablet (768–1024px), 1 column on mobile (<768px)

#### Scenario: Featured products are filtered from full product list
- **WHEN** the homepage fetches products
- **THEN** it calls `getProducts(1, 100)` and filters the response with `.products.filter(p => p.is_featured)` (no separate `getFeaturedProducts()` API needed). The explicit `limit: 100` ensures featured products beyond the default page size of 20 are included.

#### Scenario: Each featured product shows card with key info
- **WHEN** featured products render
- **THEN** each product card shows: product image (or gradient placeholder), product name, and price formatted using the shared `formatPrice(cents)` utility

#### Scenario: Featured product cards link to detail page
- **WHEN** a user clicks a featured product card
- **THEN** they are navigated to /products/[id] for that product

#### Scenario: No featured products
- **WHEN** no products have `is_featured` set to true
- **THEN** the featured section is not rendered (heading and grid are both absent)

### Requirement: Loading state via loading.tsx
The system SHALL display skeleton placeholders during route transitions to the homepage via Next.js App Router `loading.tsx` file.

#### Scenario: Skeleton grid matches homepage layout
- **WHEN** a user navigates to / (during route transition)
- **THEN** `app/loading.tsx` renders skeleton placeholders for the hero area and featured products grid

### Requirement: Page metadata
The system SHALL export metadata for the homepage for browser tab identification.

#### Scenario: Homepage page title
- **WHEN** the homepage renders
- **THEN** the browser tab shows "Atelier Marie | Luxury Handcrafted Candles"
