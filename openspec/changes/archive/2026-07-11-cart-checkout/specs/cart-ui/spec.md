## ADDED Requirements

### Requirement: Cart context provides global cart state
The system SHALL provide a React Context (`CartContext`) that exposes current cart items, total in cents, item count, loading state, and error state to all descendant components. The context SHALL fetch the cart from the API on initial mount and update local state after every cart mutation.

#### Scenario: Cart hydrates on app load
- **WHEN** the app mounts in the browser
- **THEN** the CartProvider calls `GET /v1/cart` and populates items, total_cents, and item_count from the response

#### Scenario: Cart state available to any component
- **WHEN** a component calls `useCart()` inside the CartProvider tree
- **THEN** it receives the current items array, total_cents, item_count, isLoading, and error values

#### Scenario: Cart fetch failure does not crash the app
- **WHEN** the initial `GET /v1/cart` request fails (network error or 500)
- **THEN** the cart state remains empty (items: [], total_cents: 0, item_count: 0) and error is set with a message

### Requirement: Add to cart with optimistic update
The system SHALL provide an `addToCart(productId, quantity?)` function via CartContext that optimistically updates the local item count and fires `POST /v1/cart`. On success, the full server response SHALL replace local state. On failure, the system SHALL revert to previous state and set an error message.

#### Scenario: Successful add to cart
- **WHEN** user triggers `addToCart("lavender-dreams-300ml", 1)`
- **THEN** item_count increments immediately, the API is called, and on success the full CartResponse replaces local state

#### Scenario: Add to cart fails due to stock
- **WHEN** user triggers `addToCart` and the API returns 409 (insufficient stock)
- **THEN** the optimistic increment is reverted and error is set to a user-friendly stock message

#### Scenario: Add to cart with default quantity
- **WHEN** `addToCart("product-id")` is called without a quantity argument
- **THEN** quantity defaults to 1

### Requirement: Update cart item quantity
The system SHALL provide an `updateQuantity(productId, quantity)` function that optimistically updates the displayed quantity and calls `PATCH /v1/cart/{productId}`. On failure, it SHALL revert to previous state.

#### Scenario: Increment quantity
- **WHEN** user increments quantity for "lavender-dreams-300ml" from 1 to 2
- **THEN** the displayed quantity updates immediately, `PATCH /v1/cart/lavender-dreams-300ml` is called with `{quantity: 2}`, and on success server state replaces local state

#### Scenario: Quantity update fails
- **WHEN** the PATCH request returns an error
- **THEN** the quantity reverts to its previous value and error is shown

### Requirement: Remove item from cart
The system SHALL provide a `removeItem(productId)` function that optimistically removes the item from the local list and calls `DELETE /v1/cart/{productId}`. On failure, it SHALL restore the item.

#### Scenario: Successful remove
- **WHEN** user removes "lavender-dreams-300ml" from cart
- **THEN** the item disappears immediately, `DELETE /v1/cart/lavender-dreams-300ml` is called, and on success server state replaces local state

#### Scenario: Remove fails
- **WHEN** the DELETE request fails
- **THEN** the item reappears in its original position and error is set

### Requirement: Cart drawer slides in from the right
The system SHALL render a drawer panel that slides in from the right edge of the viewport with a semi-transparent backdrop overlay. The drawer SHALL display all cart items with product name, price, quantity controls (increment/decrement), a remove button, and the cart subtotal at the bottom.

#### Scenario: Drawer opens on cart icon click
- **WHEN** user clicks the cart icon in the header
- **THEN** the drawer slides in from the right with a backdrop overlay and body scroll is locked

#### Scenario: Drawer opens after add-to-cart
- **WHEN** user adds an item to the cart
- **THEN** the drawer opens automatically showing the updated cart contents

#### Scenario: Drawer closes on backdrop click
- **WHEN** the drawer is open and user clicks the backdrop overlay
- **THEN** the drawer slides out and body scroll is restored

#### Scenario: Drawer closes on close button
- **WHEN** user clicks the X close button in the drawer header
- **THEN** the drawer slides out and body scroll is restored

#### Scenario: Drawer closes on Escape key
- **WHEN** the drawer is open and user presses Escape
- **THEN** the drawer closes

#### Scenario: Empty cart state in drawer
- **WHEN** the drawer is open and cart has no items
- **THEN** a message "Your cart is empty" is shown with a "Continue Shopping" link

### Requirement: Cart badge shows live item count
The system SHALL display a badge on the cart icon in the header showing the current `item_count` from CartContext. The badge SHALL be hidden when count is 0 and SHALL animate briefly when the count changes.

#### Scenario: Badge visible with items
- **WHEN** the cart has 3 items (item_count = 3)
- **THEN** a badge displaying "3" appears on the cart icon

#### Scenario: Badge hidden when empty
- **WHEN** the cart is empty (item_count = 0)
- **THEN** no badge is shown on the cart icon

#### Scenario: Badge animates on change
- **WHEN** item_count changes from 2 to 3
- **THEN** the badge briefly scales up (bounce animation) to draw attention

### Requirement: Add-to-cart button on product cards and detail page
The system SHALL display an "Add to Cart" button on each product card and on the product detail page. Clicking the button SHALL call `addToCart`, show a brief checkmark animation on the button, and update the header badge.

#### Scenario: Add to cart from product card
- **WHEN** user clicks "Add to Cart" on a product card
- **THEN** the button shows a checkmark icon briefly, the badge increments, and the cart drawer opens

#### Scenario: Add to cart from product detail page
- **WHEN** user clicks "Add to Cart" on the product detail page
- **THEN** the button shows a checkmark animation, badge updates, and drawer opens

#### Scenario: Button disabled while processing
- **WHEN** an add-to-cart request is in flight for a product
- **THEN** the button is disabled and shows a loading indicator until the request resolves

#### Scenario: Out-of-stock product
- **WHEN** a product has stock = 0
- **THEN** the "Add to Cart" button is replaced with "Out of Stock" (disabled)

### Requirement: Drawer respects reduced motion preference
The system SHALL use `motion-safe:` Tailwind prefix for all cart animations so that users with `prefers-reduced-motion: reduce` see instant state changes without transitions.

#### Scenario: Reduced motion enabled
- **WHEN** the user has `prefers-reduced-motion: reduce` set in their OS
- **THEN** the drawer appears/disappears instantly, badge does not animate, and checkmark shows without transition

### Requirement: Drawer implements focus trap
The system SHALL trap keyboard focus within the cart drawer while it is open. Tab and Shift+Tab SHALL cycle through interactive elements inside the drawer only. Focus SHALL move to the drawer's close button when it opens, and return to the cart icon button when it closes.

#### Scenario: Focus trapped while drawer open
- **WHEN** the drawer is open and user presses Tab repeatedly
- **THEN** focus cycles through the drawer's interactive elements (close button, quantity controls, remove buttons, checkout link) without escaping to the page behind

#### Scenario: Focus restored on close
- **WHEN** the drawer closes
- **THEN** focus returns to the cart icon button that triggered it
