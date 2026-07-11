## ADDED Requirements

### Requirement: Product detail page displays full product information
The system SHALL render a product detail page at /products/[id] showing the product image, name, price, description, category, materials, and crafting time.

#### Scenario: Detail page renders product info
- **WHEN** a user navigates to /products/[id]
- **THEN** the page displays: large product image (or gradient placeholder), product name in Playfair Display, price as €XX.XX, category badge, and full description

#### Scenario: Materials and crafting time display when available
- **WHEN** a product has non-null `materials`
- **THEN** a "Materials & Ingredients" section displays the materials text

#### Scenario: Crafting time displays when available
- **WHEN** a product has non-null `days_to_craft`
- **THEN** a "Crafting Time" detail displays (e.g., "Lovingly handcrafted over 3 days")

#### Scenario: Null description handled gracefully
- **WHEN** a product has `description` as null
- **THEN** the description section is not rendered (no empty space or placeholder text)

#### Scenario: Two-column layout on desktop
- **WHEN** viewport width is above 1024px
- **THEN** the image occupies the left column and product details occupy the right column

#### Scenario: Single-column layout on mobile
- **WHEN** viewport width is below 1024px
- **THEN** the image stacks above the product details in a single column

#### Scenario: Product not found (invalid ID)
- **WHEN** a user navigates to /products/[id] with an ID that does not exist
- **THEN** `page.tsx` calls `notFound()` from `next/navigation`, rendering `app/products/[id]/not-found.tsx` with a friendly "Product not found" message and a link back to /products (HTTP 404 response)

#### Scenario: Inactive product treated as not found
- **WHEN** a user navigates to /products/[id] for a product with `is_active: false`
- **THEN** the page checks `is_active` FIRST (before checking stock), calls `notFound()`, and displays the same treatment as an invalid ID

#### Scenario: Decision tree for product states
- **WHEN** `page.tsx` receives a product response
- **THEN** it applies this logic in order: (1) if product not found or fetch throws → `notFound()`; (2) if `is_active === false` → `notFound()`; (3) if `stock === 0` → render page with disabled "Out of Stock" button, NO QuantitySelector; (4) if `stock > 0` → render full page with QuantitySelector + "Add to Cart"

### Requirement: Product image display with next/image
The system SHALL render the product image using next/image with responsive sizing appropriate for the detail view.

#### Scenario: Large image with correct sizes
- **WHEN** a product has a non-null `image_url`
- **THEN** the image renders via next/image with `sizes="(max-width: 1024px) 100vw, 50vw"`, aspect ratio 4:5, and `priority` loading (the product image is always the primary visual content of the page)

#### Scenario: Gradient placeholder for missing image
- **WHEN** a product has `image_url` as null OR the image fails to load (404/timeout)
- **THEN** a large CSS gradient placeholder renders (warm-ivory → dusty-pink, 135deg) with the product name centered in Playfair Display. Uses `role="img"` and `aria-label={product.name}` for accessibility.

### Requirement: Quantity selector
The system SHALL provide a quantity selector allowing users to choose how many units to add to cart.

#### Scenario: Default quantity is 1
- **WHEN** the product detail page loads
- **THEN** the quantity selector displays 1

#### Scenario: Increment quantity
- **WHEN** a user clicks the "+" button
- **THEN** the quantity increases by 1

#### Scenario: Decrement quantity
- **WHEN** a user clicks the "−" button and quantity is greater than 1
- **THEN** the quantity decreases by 1

#### Scenario: Minimum quantity is 1
- **WHEN** the quantity is 1 and user clicks "−"
- **THEN** the quantity remains 1 and the "−" button appears disabled

#### Scenario: Maximum quantity respects available stock
- **WHEN** the quantity reaches `Math.min(10, product.stock)`
- **THEN** the quantity cannot increase further and the "+" button appears disabled

#### Scenario: QuantitySelector not rendered for out-of-stock
- **WHEN** a product has `stock: 0`
- **THEN** the QuantitySelector component is NOT rendered (only the disabled "Out of Stock" button appears)

#### Scenario: Quantity buttons meet touch target requirements
- **WHEN** the quantity selector renders
- **THEN** both "+" and "−" buttons have a minimum touch target of 44×44px

#### Scenario: Quantity is keyboard accessible
- **WHEN** a keyboard user focuses the quantity controls
- **THEN** buttons are activatable with Enter/Space and the current quantity is announced to screen readers via aria-label (e.g., "Quantity: 3")

### Requirement: Add to Cart button
The system SHALL display an "Add to Cart" button that provides visual and accessible feedback on click.

#### Scenario: Add to Cart button renders
- **WHEN** the product detail page loads for an in-stock product
- **THEN** a primary Button (muted-gold) labeled "Add to Cart" is visible

#### Scenario: Click provides visual and accessible confirmation
- **WHEN** a user clicks "Add to Cart"
- **THEN** the button text changes to "Added ✓" for 1.5 seconds, then reverts to "Add to Cart". Screen readers announce the confirmation via an `aria-live="polite"` status region. Day 3 implementation: `console.log` the product ID and quantity (no actual API call).

#### Scenario: Button is non-interactive during confirmation
- **WHEN** the button shows "Added ✓" (during the 1.5s confirmation period)
- **THEN** additional clicks are ignored (button is disabled or click handler is debounced)

#### Scenario: Out of stock product
- **WHEN** a product has `stock: 0`
- **THEN** the "Add to Cart" button is disabled and shows "Out of Stock"

#### Scenario: Button uses selected quantity
- **WHEN** a user sets quantity to 3 and clicks "Add to Cart"
- **THEN** the action is invoked with the product ID and quantity 3

### Requirement: Product detail loading state
The system SHALL display skeleton placeholders while the product detail data is loading (shown during route navigation via `loading.tsx`).

#### Scenario: Loading skeleton matches detail layout
- **WHEN** a user navigates to a product detail page (during route transition)
- **THEN** skeleton placeholders render matching the two-column layout: image skeleton on left, text skeletons for name/price/description on right

### Requirement: Page metadata
The system SHALL export metadata for the product detail page for browser tab identification.

#### Scenario: Product detail page title
- **WHEN** the product detail page renders
- **THEN** the browser tab shows "[Product Name] | Atelier Marie" via an async `generateMetadata({ params })` function (NOT a static metadata export, since the title depends on route params)
