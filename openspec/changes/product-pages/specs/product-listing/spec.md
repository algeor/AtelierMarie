## ADDED Requirements

### Requirement: Product grid displays all active products
The system SHALL display all active products in a responsive grid on the /products page. The page fetches `getProducts(1, 100)` explicitly (overriding the default limit of 20) to support client-side filtering. The API already returns only active products; the page does not re-filter by `is_active`.

#### Scenario: Products render in responsive grid
- **WHEN** the /products page loads
- **THEN** all products returned by the API render in a grid: 4 columns on desktop (>1024px), 2 columns on tablet (768–1024px), 1 column on mobile (<768px)

#### Scenario: Page title displays
- **WHEN** the /products page loads
- **THEN** the heading "Our Collection" is visible in Playfair Display

#### Scenario: Server/Client Component boundary
- **WHEN** the /products page renders
- **THEN** `app/products/page.tsx` is a Server Component that fetches all products and passes them as props to a `ProductListingClient` component (marked `'use client'`) which manages category filter state and renders CategoryFilter + ProductGrid

### Requirement: Product card shows image, name, and price
Each product in the grid SHALL render as a card with the product image (or gradient placeholder), product name, and formatted price.

#### Scenario: Card with image
- **WHEN** a product has a non-null `image_url`
- **THEN** the card renders the image via next/image with lazy loading and `sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw"`

#### Scenario: Card without image shows gradient placeholder
- **WHEN** a product has `image_url` as null OR the image fails to load
- **THEN** the card renders a CSS gradient placeholder (warm-ivory → dusty-pink, 135deg) with the product name centered in Playfair Display. Placeholder uses `role="img"` and `aria-label={product.name}`.

#### Scenario: Price displays in euros from cents
- **WHEN** a product card renders
- **THEN** the price displays as €XX.XX using a shared `formatPrice(cents)` utility (e.g., price_cents 3200 → "€32.00", price_cents 100 → "€1.00"). Always shows two decimal places with period separator and € prefix.

#### Scenario: Card hover animation
- **WHEN** a user hovers over a product card on desktop
- **THEN** the card applies a subtle scale transform (1.02) with 200ms ease transition, using Tailwind's `motion-safe:` prefix to respect `prefers-reduced-motion: reduce`

#### Scenario: Card links to product detail
- **WHEN** a user clicks a product card
- **THEN** they navigate to /products/[id]. The entire card is wrapped in a `<Link>` element (no nested interactive elements inside).

#### Scenario: Product name overflow
- **WHEN** a product name is longer than 2 lines at the card width
- **THEN** the name is clamped at 2 lines with ellipsis (`line-clamp-2`) to preserve grid alignment

### Requirement: Category filter pills
The system SHALL display category filter pills above the product grid. Selecting a category filters products instantly without page reload.

#### Scenario: Filter pills render from available categories
- **WHEN** the /products page loads
- **THEN** an "All" pill renders first, followed by unique non-null category values from the product list (e.g., Floral, Woody, Fresh, Gourmand). Products with `category: null` appear under "All" but do not generate their own pill. If fewer than 2 total categories exist (only "All"), the entire filter section is hidden.

#### Scenario: Category pills overflow on mobile
- **WHEN** more than ~5 category pills exist on a mobile viewport
- **THEN** the pills container uses `overflow-x-auto` for horizontal scrolling (no wrapping). On desktop, pills wrap to multiple rows.

#### Scenario: "All" is selected by default
- **WHEN** the /products page loads
- **THEN** the "All" pill has the active/selected style (muted-gold background)

#### Scenario: Selecting a category filters the grid
- **WHEN** a user clicks a category pill (e.g., "Floral")
- **THEN** only products matching that category display in the grid, and the selected pill gets the active style

#### Scenario: Selecting "All" shows all products
- **WHEN** a user clicks the "All" pill after filtering
- **THEN** all products display again

#### Scenario: No products match category
- **WHEN** a user selects a category that has no products
- **THEN** a friendly empty state message displays (e.g., "No products found in this category")

#### Scenario: Filter results announced to screen readers
- **WHEN** a category filter is applied
- **THEN** a visually-hidden `<div aria-live="polite" role="status">` updates its text content with the result count (e.g., "Showing 2 products in Floral" or "Showing 4 products" for All)

#### Scenario: Filter pills use accessible ARIA pattern
- **WHEN** the filter pills render
- **THEN** they use `<button>` elements with `aria-pressed="true|false"` wrapped in a `<div role="group" aria-label="Filter by category">`

#### Scenario: Filter pills are keyboard accessible
- **WHEN** a keyboard user tabs to the filter pills
- **THEN** each pill is focusable and activatable with Enter/Space, with visible focus rings

### Requirement: Product image uses next/image with responsive srcset
The system SHALL render product images using the next/image component with appropriate responsive sizing.

#### Scenario: Image has correct sizes for grid context
- **WHEN** a product image renders in the product grid
- **THEN** the next/image component has `sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw"`

#### Scenario: Images lazy load below the fold
- **WHEN** product images are below the viewport fold
- **THEN** they use lazy loading (default next/image behavior)

#### Scenario: Image has proper alt text
- **WHEN** a product image renders
- **THEN** the alt text is the product name

### Requirement: Loading state via loading.tsx
The system SHALL display skeleton placeholders during route transitions via Next.js App Router `loading.tsx` file.

#### Scenario: Skeleton grid matches product card layout
- **WHEN** a user navigates to /products (during route transition)
- **THEN** `app/products/loading.tsx` renders skeleton placeholders in the same grid layout with shapes matching the card image area, title, and price

### Requirement: Error state for API failures
The system SHALL display a friendly error message if product data fails to load.

#### Scenario: API fetch failure shows error state
- **WHEN** the product data fetch fails (network error, server error)
- **THEN** a friendly error message displays ("Unable to load products. Please try again later.") with an optional retry button

#### Scenario: Error boundary catches runtime errors
- **WHEN** a runtime error occurs on the products page
- **THEN** `app/products/error.tsx` displays a branded error message with a retry button instead of a blank page
