# Product Pages — Spec

## ADDED Requirements

### Requirement: Responsive Product Grid

Products are displayed in a responsive grid that adapts column count to viewport width while maintaining a luxury card aesthetic.

#### Scenario: Product grid renders correct columns per breakpoint

WHEN the /shop page loads on a desktop viewport (>1024px)
THEN the product grid displays 4 columns
WHEN the viewport is tablet (768–1024px)
THEN the product grid displays 2 columns
WHEN the viewport is mobile (<768px)
THEN the product grid displays 1 column
AND consistent gap spacing (16–24px) is maintained between cards at all breakpoints

#### Scenario: Product grid handles empty state

WHEN the product grid receives no products (e.g., filter returns zero results)
THEN a friendly empty state message is displayed (e.g., "No products found")
AND a suggestion to clear filters or browse all products is shown

#### Scenario: Product grid displays loading skeletons

WHEN products are being fetched from the API
THEN skeleton card placeholders are shown in the grid
AND the skeletons pulse with a subtle animation
AND the number of skeletons matches the expected column count

### Requirement: Product Card Design

Each product card displays essential product information with quick interaction options.

#### Scenario: Product card renders complete information

WHEN a product card is displayed in the grid
THEN it shows the product image (or gradient placeholder)
AND the product name in Playfair Display font
AND the product price formatted with currency symbol (€)
AND a wishlist heart icon in the top-right corner of the image
AND the card has cream background with rounded corners and hover shadow

#### Scenario: Product card shows "Quick add" for simple products

WHEN a product has no variants (single scent, single size)
THEN the card displays a "Quick add" button
WHEN the user clicks "Quick add"
THEN the product is added to the cart immediately
AND the cart badge increments
AND a brief confirmation animation plays on the button

#### Scenario: Product card shows "Choose options" for variant products

WHEN a product has multiple variants (scents or sizes)
THEN the card displays a "Choose options" button instead of "Quick add"
WHEN the user clicks "Choose options"
THEN they are navigated to the product detail page (PDP)

#### Scenario: Product card wishlist interaction

WHEN a user clicks the heart icon on a product card
THEN the heart fills with dusty pink color
AND the state toggles (filled → outline on second click)

### Requirement: Product Detail Page (PDP)

The PDP provides complete product information with variant selection, purchase actions, and supplementary content.

#### Scenario: PDP displays product information and gallery

WHEN a user navigates to /products/{slug}
THEN the page displays an image gallery (main image + thumbnails if multiple)
AND the product title in large Playfair Display heading
AND the product price
AND scent selector (if multiple scents available) as clickable chips or dropdown
AND size selector (if multiple sizes) as clickable chips
AND burn time metadata
AND wax type metadata

#### Scenario: PDP variant selection updates display

WHEN a user selects a different scent or size variant
THEN the displayed price updates if variants have different prices
AND the gallery image updates if variant-specific images exist
AND the selection is visually highlighted (muted gold border)

#### Scenario: PDP quantity and purchase controls

WHEN the PDP renders
THEN a quantity selector is displayed with – and + buttons (minimum 1)
AND an "Add to cart" button (primary style, muted gold)
AND a "Buy now" button (secondary style)
WHEN the user clicks "Add to cart"
THEN the selected variant and quantity are added to the cart
AND the cart drawer opens to confirm
WHEN the user clicks "Buy now"
THEN the item is added to cart and user is directed to checkout flow

#### Scenario: PDP accordions provide supplementary information

WHEN the PDP renders below the purchase controls
THEN a "Candle Care" accordion is displayed (collapsed by default) with care instructions
AND a "Shipping & Returns" accordion is displayed (collapsed by default) with shipping info
WHEN a user clicks an accordion header
THEN it expands to reveal the content with smooth animation

#### Scenario: PDP recommended products section

WHEN the PDP renders below the accordions
THEN a "You may also like" section displays recommended products
AND it fetches from GET /v1/recommendations?product_id={id}
AND it displays 4 product cards on desktop (2 on mobile) in a horizontal row or grid

### Requirement: Impression Tracking

Product visibility in the grid is tracked for analytics using IntersectionObserver.

#### Scenario: Product impression is recorded after visibility threshold

WHEN a product card enters the viewport and remains visible for at least 1 second
THEN a product_impression event is emitted with product_id and grid_position
AND the event is only emitted once per product per page load (no duplicate impressions)

#### Scenario: Impression tracking does not fire for partially hidden cards

WHEN a product card is less than 50% visible in the viewport
THEN no impression event is emitted
WHEN the card becomes more than 50% visible and stays for 1 second
THEN the impression event fires

### Requirement: Shop Page Filtering and Sorting

The /shop page provides category filtering and sort controls for product discovery.

#### Scenario: Category filter narrows product display

WHEN a user selects a category filter (e.g., "Dessert candles")
THEN only products in that category are displayed in the grid
AND the active filter is visually indicated
AND a "Clear filter" option is available

#### Scenario: Sort controls reorder products

WHEN a user selects a sort option (e.g., "Price: low to high", "Price: high to low", "Newest")
THEN the product grid reorders accordingly
AND the selected sort option is visually indicated in the control
