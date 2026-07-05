# Cart Drawer — Spec

## ADDED Requirements

### Requirement: Slide-in Cart Drawer

The cart drawer provides a non-disruptive way to review and manage cart contents without leaving the current page.

#### Scenario: Cart drawer opens from the right

WHEN a user clicks the cart icon in the header
THEN a drawer panel slides in from the right edge of the viewport
AND a semi-transparent dark overlay covers the rest of the page
AND the body scroll is locked while the drawer is open
AND the drawer width is approximately 400px on desktop, full-width on mobile
AND the drawer has a header with "Your Cart" title and a close (X) button

#### Scenario: Cart drawer closes

WHEN a user clicks the close (X) button in the drawer header
THEN the drawer slides out to the right and the overlay fades
WHEN a user clicks the semi-transparent overlay
THEN the drawer closes
WHEN a user presses the Escape key
THEN the drawer closes
AND body scroll is restored in all cases

#### Scenario: Cart drawer opens after adding an item

WHEN a user clicks "Add to cart" on a PDP or "Quick add" on a product card
THEN the cart drawer opens automatically to confirm the addition
AND the newly added item is visible (scrolled into view if necessary)

### Requirement: Cart Item Display and Controls

Each item in the cart displays product details with quantity adjustment and removal capabilities.

#### Scenario: Cart item row displays complete information

WHEN an item is present in the cart
THEN the cart drawer displays a row with: product thumbnail image, product name, selected variant (scent/size if applicable), unit price, quantity controls, and line subtotal
AND items are listed in the order they were added (most recent at top)

#### Scenario: Quantity increase updates totals

WHEN a user clicks the "+" button on a cart item
THEN the item quantity increments by 1
AND the line subtotal updates immediately (quantity x unit price)
AND the cart total at the bottom updates immediately
AND the cart badge in the header updates

#### Scenario: Quantity decrease updates totals

WHEN a user clicks the "−" button on a cart item with quantity > 1
THEN the item quantity decrements by 1
AND the line subtotal and cart total update immediately
WHEN the quantity is already 1 and the user clicks "−"
THEN the item is removed from the cart (or a confirmation is shown)

#### Scenario: Remove button removes item from cart

WHEN a user clicks the remove (trash/X) button on a cart item
THEN the item is removed from the cart
AND the item row disappears with a fade-out transition
AND the cart total updates
AND the cart badge updates

### Requirement: Cart Totals and Checkout

The cart drawer displays order totals and a path to checkout.

#### Scenario: Cart totals are displayed correctly

WHEN items are in the cart
THEN the bottom of the drawer shows: Subtotal (sum of all line subtotals), Estimated total (same as subtotal for MVP, shipping TBD)
AND a prominent "Checkout" button is displayed below the totals (primary style, full-width)

#### Scenario: Optimistic UI with server sync

WHEN a user modifies cart quantities or removes items
THEN the UI updates immediately (optimistic)
AND a background request syncs the cart state to POST /v1/cart
AND if the sync fails, the cart does not revert (error is logged silently for MVP)

### Requirement: Empty Cart State

When the cart has no items, a helpful empty state encourages further browsing.

#### Scenario: Empty cart displays message and link

WHEN the cart drawer opens and there are no items
THEN a centered message is displayed: "Your cart is empty"
AND a "Continue shopping" link is displayed below the message
WHEN the user clicks "Continue shopping"
THEN the cart drawer closes and the user is navigated to /shop

#### Scenario: Cart becomes empty after removing last item

WHEN a user removes the last item from the cart
THEN the item rows disappear
AND the empty state message and "Continue shopping" link appear
AND the cart badge in the header disappears (no badge shown for 0 items)
